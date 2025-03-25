from datetime import datetime
from fastapi import HTTPException
from ..utils.verify_email import is_email_valid
from ..utils.logger import get_logger
from ..adapters.token_adapter import TokenAdapter
from ..adapters.password_adapter import PasswordAdapter
from ..interfaces.login_user import LoginUser
from ..interfaces.create_user import CreateUser
from ..interfaces.update_user import UpdateUser
from ..interfaces.create_subscriptions import CreateSubscriptions
from ..repositories.user_repository import UserRepository
from ..utils.error_handler import raise_http_error
from src.config.settings import Settings


settings = Settings()
logger = get_logger(__name__)


class UserUseCases:
    def __init__(self):
        self.user_repository = UserRepository()
        self.password_adapter = PasswordAdapter()
        self.token_adapter = TokenAdapter()
    
    async def add_user(self, admin_profile, admin_id, user: CreateUser, audit_data=None):
       """Add a new user after validating their data."""
       try:
           
           user_data = user.dict()
           

           required_fields = ["full_name", "email", "password", "profile"]
           for field in required_fields:
               if field not in user_data or not user_data[field]:
                   logger.error(f"Error adding user: {field} cannot be empty")
                   raise_http_error(400, f"Error adding user: {field} cannot be empty")
           

           valid_profiles = ["general_administrator", "administrator", "professional"]
           if user_data["profile"] not in valid_profiles:
               logger.error(f"Error adding user: Invalid profile")
               raise_http_error(422, f"Invalid profile. Should be one of: {', '.join(valid_profiles)}")
           

           if "status" in user_data and user_data["status"] not in ["active", "inactive"]:
               logger.error(f"Error adding user: Invalid status")
               raise_http_error(422, "Invalid status. Should be 'active' or 'inactive'")
           

           if not is_email_valid(user_data["email"]):
               logger.error(f"Error adding user: Invalid email")
               raise_http_error(422, "Invalid email format")
           

           user_exists = await self.user_repository.get_user_by_email(user_data["email"])
           if user_exists:
               logger.error("Error adding user: User already exists")
               raise_http_error(409, "User with this email already exists")
            
           if user_data["profile"] == "professional" and admin_profile != "general_administrator":

               admin_exists = await self.user_repository.get_user_by_id(admin_id)
               if not admin_exists:
                   logger.error(f"Error adding user: Admin with ID {admin_id} not found")
                   raise_http_error(404, "Admin not found")
               
               elif admin_exists["profile"] != "administrator":
                   logger.error(f"Error adding user: User with ID {admin_id} is not an administrator")
                   raise_http_error(403, "User is not an administrator")

               else:
                    user_data["admin_id"] = admin_id 
           

           user_data["password_hash"] = await self.password_adapter.hash_password(user_data["password"])
           

           result = await self.user_repository.add_user(user_data)
           
           if result["added"]:
               return {
                   "detail": {
                       "message": "User added successfully",
                       "user_id": result["user_id"],
                       "status_code": 201
                   }
               }
           else:
               logger.error("Error adding user: User not added")
               raise_http_error(500, "Error adding user to database")
               
       except HTTPException as http_exc:
           raise http_exc
       except Exception as e:
           logger.error(f"Unexpected error when adding user: {e}")
           raise_http_error(500, "Unexpected error when adding user")
    
    async def login_user(self, user: LoginUser, audit_data=None):
        """Authenticate a user and generate a token."""
        try:
            
            user_login = user.dict()
            email = user_login["email"]
            

            user_info = await self.user_repository.get_user_by_email(email)
            
            if not user_info:
                logger.error(f"Login attempt failed: User {email} not found")
                raise_http_error(404, "User not found")

            if user_info["status"] != "active":
                logger.error(f"Login attempt failed: User {email} is inactive")
                raise_http_error(403, "User account is inactive")


            if not await self.password_adapter.verify_password(
                user_login["password"], user_info["password_hash"]
            ):
                logger.error(f"Login attempt failed: Incorrect password for {email}")
                raise_http_error(401, "Incorrect password")


            token = await self.token_adapter.create_token(
                user_info["id"],
                user_info["full_name"],
                email,
                user_info["profile"],
                user_info.get("admin_id")
            )

            logger.info(f"User {email} logged in successfully")

            return {
                "detail": {
                    "message": "Login successful",
                    "user_name": user_info["full_name"],
                    "user_id": user_info["id"],
                    "profile": user_info["profile"],
                    "token": token,
                    "status_code": 200,
                }
            }
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            raise_http_error(500, "Internal server error during login process")
    
    async def get_users(self, admin_id=None, audit_data=None):
        """
        Retrieve all users or users associated with an admin.
        If admin_id is provided, return only users associated with that admin.
        """
        try:

            users = await self.user_repository.get_users(admin_id)


            users_without_password = [
                {key: user[key] for key in user if key != 'password_hash'} 
                for user in users
            ]

            return {
                "detail": {
                    "message": "Users retrieved successfully",
                    "users": users_without_password,
                    "count": len(users_without_password),
                    "status_code": 200
                }
            }
        except Exception as e:
            logger.error(f"Error retrieving users: {e}")
            raise_http_error(500, "Error retrieving users")

    async def get_user_by_id(self, user_id: str, audit_data=None):
        """Retrieve a user by their ID, excluding the password."""
        try:

            user = await self.user_repository.get_user_by_id(user_id)

            if user:

                user_without_password = {
                    key: user[key] for key in user if key != 'password_hash'
                }
                
                return {
                    "detail": {
                        "message": "User retrieved successfully",
                        "user": user_without_password,
                        "status_code": 200
                    }
                }
            else:
                logger.error(f"User with ID {user_id} not found")
                raise_http_error(404, "User not found")
                
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error retrieving user by ID: {e}")
            raise_http_error(500, "Error retrieving user")
    
    async def update_user(self, current_user_id, current_user_profile, user_id: str, user: UpdateUser, audit_data=None):
        """Update user information."""
        try:

            existing_user = await self.user_repository.get_user_by_id(user_id)
            if not existing_user:
                logger.error(f"Error updating user: User with ID {user_id} not found")
                raise_http_error(404, "User not found")


            user_data = user.dict(exclude_unset=True)

            email_exists = await self.user_repository.get_user_by_email(user_data.get("email"))
            if email_exists and email_exists["id"] != user_id:
                logger.error("Error updating user: Email already in use")
                raise_http_error(409, "Email already in use")
            

            if "email" in user_data and not is_email_valid(user_data["email"]):
                logger.error("Error updating user: Invalid email format")
                raise_http_error(422, "Invalid email format")
                

            if "profile" in user_data:
                valid_profiles = ["general_administrator", "administrator", "professional"]
                if user_data["profile"] not in valid_profiles:
                    logger.error("Error updating user: Invalid profile")
                    raise_http_error(422, f"Invalid profile. Should be one of: {', '.join(valid_profiles)}")
            

            if "status" in user_data and user_data["status"] not in ["active", "inactive"]:
                logger.error("Error updating user: Invalid status")
                raise_http_error(422, "Invalid status. Should be 'active' or 'inactive'")
            
            if current_user_profile != "general_administrator" and existing_user["id"] != current_user_id:

                current_user = await self.user_repository.get_user_by_id(current_user_id)
                if not current_user:
                    logger.error(f"Error updating user: User with ID {current_user_id} not found")
                    raise_http_error(404, "Admin not found")
                
                elif current_user["profile"] != "administrator":
                    logger.error(f"Error updating user: User with ID {current_user_id} is not an administrator")
                    raise_http_error(403, "User is not an administrator")
                

                if current_user["profile"] == "administrator":  
                    if existing_user["admin_id"] != current_user_id:
                        logger.error(f"Error updating user: Professional with ID {user_id} is not associated with this administrator")
                        raise_http_error(403, "Professional is not associated with this administrator")
                

            if "password_hash" in user_data:
                user_data["password_hash"] = await self.password_adapter.hash_password(user_data["password_hash"])


            result = await self.user_repository.update_user(user_id, user_data)
            
            if result["updated"]:
                return {
                    "detail": {
                        "message": "User updated successfully",
                        "user_id": user_id,
                        "status_code": 200
                    }
                }
            else:
                logger.error(f"Failed to update user with ID {user_id}")
                raise_http_error(500, "Failed to update user")

        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            raise_http_error(500, "Error updating user")

    async def delete_user(self, current_user_id, current_user_profile, user_id: str, audit_data=None):
        """Delete a user by ID."""
        try:


            existing_user = await self.user_repository.get_user_by_id(user_id)
            if not existing_user:
                logger.error(f"Error deleting user: User with ID {user_id} not found")
                raise_http_error(404, "User not found")
            
            if existing_user["id"] == current_user_id:
                logger.error(f"Error deleting user: User cannot delete itself")
                raise_http_error(403, "User cannot delete itself")
            
            if current_user_profile != "general_administrator" and existing_user["id"] != current_user_id:

                current_user = await self.user_repository.get_user_by_id(current_user_id)
                if not current_user:
                    logger.error(f"Error deleting user: User with ID {current_user_id} not found")
                    raise_http_error(404, "Admin not found")
                

                if existing_user["admin_id"] != current_user_id:
                    logger.error(f"Error deleting user: Professional with ID {user_id} is not associated with this administrator")
                    raise_http_error(403, "Professional is not associated with this administrator")


            result = await self.user_repository.delete_user(user_id)
            
            if result["deleted"]:
                logger.info(f"User with ID {user_id} deleted successfully")
                return {
                    "detail": {
                        "message": "User deleted successfully",
                        "user_id": user_id,
                        "status_code": 200
                    }
                }
            else:
                logger.error(f"Failed to delete user with ID {user_id}")
                raise_http_error(500, "Failed to delete user")

        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            raise_http_error(500, "Error deleting user")
            
    async def get_administrators(self, audit_data=None):
        """Retrieve all administrator users."""
        try:
            administrators = await self.user_repository.get_administrators()

            return {
                "detail": {
                    "message": "Administrators retrieved successfully",
                    "administrators": administrators,
                    "count": len(administrators),
                    "status_code": 200
                }
            }
        except Exception as e:
            logger.error(f"Error retrieving administrators: {e}")
            raise_http_error(500, "Error retrieving administrators")
            
    async def get_professionals(self, admin_id: str, current_user_profile, audit_data=None):
        """Retrieve all professionals associated with an administrator."""
        try:
            if current_user_profile == "general_administrator":
                professionals = await self.user_repository.get_professionals()
            else:

                admin = await self.user_repository.get_user_by_id(admin_id)
                if not admin:
                    logger.error(f"Error retrieving professionals: Admin with ID {admin_id} not found")
                    raise_http_error(404, "Administrator not found")

                if admin["profile"] != "administrator":
                    logger.error(f"Error retrieving professionals: User with ID {admin_id} is not an administrator")
                    raise_http_error(403, "User is not an administrator")

                professionals = await self.user_repository.get_professionals_by_admin(admin_id)

            return {
                "detail": {
                    "message": "Professionals retrieved successfully",
                    "professionals": professionals,
                    "count": len(professionals),
                    "status_code": 200
                }
            }
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error retrieving professionals: {e}")
            raise_http_error(500, "Error retrieving professionals")
    

    async def create_subscription(self, subscription_data: CreateSubscriptions, audit_data=None):
        """Create a subscription for a user."""
        try:

            data_dict = subscription_data.dict()
    

            admin_exists = await self.user_repository.get_user_by_id(data_dict["admin_id"])
            if not admin_exists:
                logger.error(f"Error creating subscription: Admin with ID {data_dict['admin_id']} not found")
                raise_http_error(404, "Admin not found")
        

            subscription_exists = await self.user_repository.get_subscription_by_admin_id(data_dict["admin_id"])
            if subscription_exists:
                logger.error(f"Error creating subscription: User already has a subscription")
                raise_http_error(409, "User already has a subscription")
    

            try:
                start_date = datetime.strptime(data_dict["start_date"], "%d-%m-%Y")
                end_date = datetime.strptime(data_dict["end_date"], "%d-%m-%Y")
                

                data_dict["start_date"] = start_date
                data_dict["end_date"] = end_date
                
            except ValueError as e:
                logger.error(f"Invalid date format: {e}")
                raise_http_error(400, f"Invalid date format. Dates must be in DD-MM-YYYY format.")
    

            result = await self.user_repository.create_subscription(data_dict)
            
            if result["added"]:
                return {
                    "detail": {
                        "message": "Subscription created successfully",
                        "admin_id": data_dict["admin_id"],
                        "status_code": 201
                    }
                }
            else:
                logger.error(f"Failed to create subscription for user with ID {data_dict['admin_id']}")
                if "error" in result:
                    raise_http_error(500, f"Failed to create subscription: {result['error']}")
                else:
                    raise_http_error(500, "Failed to create subscription")
    
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            raise_http_error(500, "Error creating subscription")
    

    async def get_subscriptions(self, audit_data=None):
        """Retrieve all subscriptions."""
        try:

            user_id = audit_data.get("user_id") if audit_data else None
            logger.info(f"Retrieving subscriptions for user_id: {user_id}")
            

            if user_id:

                await self.get_user_by_id(user_id, audit_data)
            
            try:
                subscriptions = await self.user_repository.get_subscriptions(user_id)
                logger.info(f"Found {len(subscriptions)} subscriptions")
                

                return {
                    "detail": {
                        "message": "Subscriptions retrieved successfully",
                        "subscriptions": subscriptions,
                        "count": len(subscriptions),
                        "status_code": 200
                    }
                }
                
            except ValueError as e:

                if str(e) == "User not found":
                    logger.warning(f"User not found error for ID: {user_id}")
                    raise_http_error(404, "User not found")
                else:
                    raise
            
        except HTTPException as http_exc:

            raise http_exc
        except Exception as e:
            logger.error(f"Error retrieving subscriptions: {e}")
            raise_http_error(500, f"Error retrieving subscriptions: {str(e)}")
    

    async def get_subscription_by_id(self, subscription_id: str, audit_data=None):
        """Retrieve a subscription by its ID."""
        try:
            subscription = await self.user_repository.get_subscription_by_id(subscription_id)
            
            if subscription:
                return {
                    "detail": {
                        "message": "Subscription retrieved successfully",
                        "subscription": subscription,
                        "status_code": 200
                    }
                }
            else:
                logger.error(f"Subscription with ID {subscription_id} not found")
                raise_http_error(404, "Subscription not found")
            
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error retrieving subscription: {e}")
            raise_http_error(500, "Error retrieving subscription")

    
    async def update_subscription(self, subscription_id: str, subscription_data: CreateSubscriptions, audit_data=None):
        """Update an existing subscription."""
        try:

            subscription_data = subscription_data.dict()


            subscription_exists = await self.user_repository.get_subscription_by_id(subscription_id)
            if not subscription_exists:
                logger.error(f"Error updating subscription: Subscription with ID {subscription_id} not found")
                raise_http_error(404, "Subscription not found")
    

            admin_exists = await self.user_repository.get_user_by_id(subscription_data["admin_id"])
            if not admin_exists:
                logger.error(f"Error updating subscription: Admin with ID {subscription_data['admin_id']} not found")
                raise_http_error(404, "Admin not found")
    

            try:
                start_date = datetime.strptime(subscription_data["start_date"], "%d-%m-%Y")
                end_date = datetime.strptime(subscription_data["end_date"], "%d-%m-%Y")
                

                subscription_data["start_date"] = start_date
                subscription_data["end_date"] = end_date
                
            except ValueError as e:
                logger.error(f"Invalid date format: {e}")
                raise_http_error(400, f"Invalid date format. Dates must be in DD-MM-YYYY format.")
    

            result = await self.user_repository.update_subscription(subscription_id, subscription_data)
            
            if result["updated"]:
                return {
                    "detail": {
                        "message": "Subscription updated successfully",
                        "admin_id": subscription_data["admin_id"],
                        "status_code": 200
                    }
                }
            else:
                logger.error(f"Failed to update subscription for user with ID {subscription_data['admin_id']}")
                if "error" in result:
                    raise_http_error(500, f"Failed to update subscription: {result['error']}")
                else:
                    raise_http_error(500, "Failed to update subscription")
    
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            raise_http_error(500, "Error updating subscription")
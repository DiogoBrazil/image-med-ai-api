from fastapi import Request, Depends
from ..interfaces.create_user import CreateUser
from ..interfaces.update_user import UpdateUser
from ..interfaces.login_user import LoginUser
from ..interfaces.create_subscriptions import CreateSubscriptions
from ..usecases.user_usecases import UserUseCases
from ..utils.credentials_middleware import AuthMiddleware
from ..utils.logger import get_logger

logger = get_logger(__name__)

class UserController:
    def __init__(self):
        self.user_use_cases = UserUseCases()
        self.auth_middleware = AuthMiddleware()
    
    async def add_user(self, request: Request, user: CreateUser):
        """
        Adds a new user.
        Requires administrator profile.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "add_user",
            "ip_address": request.client.host
        }

        admin_id = request.state.user.get("user_id")
        admin_profile = request.state.user.get("profile")
        
        if request.state.user.get("profile") != "administrator" and request.state.user.get("profile") != "general_administrator":
            logger.warning(f"User {audit_data['user_id']} attempted to add user without admin privileges")
            return {
                "detail": {
                    "message": "Only administrators can add users",
                    "status_code": 403
                }
            }
            
        return await self.user_use_cases.add_user(admin_profile, admin_id, user, audit_data)

    async def login_user(self, request: Request, user: LoginUser):
        """
        Logs in a user.
        Does not require prior authentication.
        """
        api_key = request.headers.get('api_key')
        self.auth_middleware._verify_api_key(api_key)
        
        audit_data = {
            "email": user.email,
            "action": "login",
            "ip_address": request.client.host
        }
        
        return await self.user_use_cases.login_user(user, audit_data)

    async def get_users(self, request: Request, admin_id: str = None):
        """
        Retrieves all users.
        If admin_id is provided, returns only users associated with that admin.
        """
        print(f'REQUEST IN USERS==============================: {list(request)}')

        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_users",
            "ip_address": request.client.host
        }
        
        if request.state.user.get("profile") == "professional":
            admin_id = request.state.user.get("admin_id")
            if not admin_id:
                logger.warning(f"Professional {audit_data['user_id']} has no admin_id but attempted to get users")
                return {
                    "detail": {
                        "message": "You don't have permission to access this resource",
                        "status_code": 403
                    }
                }
        
        return await self.user_use_cases.get_users(admin_id, audit_data)

    async def get_user_by_id(self, request: Request, user_id: str):
        """
        Retrieves a user by ID.
        Users can only see their own data or, if administrators,
        data of users linked to them.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_user_by_id",
            "target_user_id": user_id,
            "ip_address": request.client.host
        }
        
        current_user_id = request.state.user.get("user_id")
        current_user_profile = request.state.user.get("profile")
        
        if user_id != current_user_id and current_user_profile != "administrator" and current_user_profile != "general_administrator":
            logger.warning(f"User {current_user_id} attempted to access data of another user {user_id}")
            return {
                "detail": {
                    "message": "You don't have permission to access this user's data",
                    "status_code": 403
                }
            }
        
        return await self.user_use_cases.get_user_by_id(user_id, audit_data)

    async def update_user(self, request: Request, user_id: str, user: UpdateUser):
        """
        Updates user information.
        Users can only update their own data or, if administrators,
        data of users linked to them.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "update_user",
            "target_user_id": user_id,
            "ip_address": request.client.host
        }
        
        current_user_id = request.state.user.get("user_id")
        current_user_profile = request.state.user.get("profile")
        
        if user_id != current_user_id and current_user_profile != "administrator" and current_user_profile != "general_administrator":
            logger.warning(f"User {current_user_id} attempted to update data of another user {user_id}")
            return {
                "detail": {
                    "message": "You don't have permission to update this user's data",
                    "status_code": 403
                }
            }
        
        return await self.user_use_cases.update_user(current_user_id, current_user_profile, user_id, user, audit_data)
    

    async def delete_user(self, request: Request, user_id: str):
        """
        Removes a user.
        Only administrators can remove users.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "delete_user",
            "target_user_id": user_id,
            "ip_address": request.client.host
        }
        
        if request.state.user.get("profile") != "administrator" and request.state.user.get("profile") != "general_administrator":
            logger.warning(f"User {audit_data['user_id']} attempted to delete user without admin privileges")
            return {
                "detail": {
                    "message": "Only administrators can delete users",
                    "status_code": 403
                }
            }
        
        current_user_id = request.state.user.get("user_id")
        current_user_profie = request.state.user.get("profile")

        return await self.user_use_cases.delete_user(current_user_id, current_user_profie, user_id, audit_data)
        
    async def get_administrators(self, request: Request):
        """
        Retrieves all administrators.
        For internal use or super administrators only.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_administrators",
            "ip_address": request.client.host
        }
        
        if request.state.user.get("profile") != "general_administrator":
            logger.warning(f"User {audit_data['user_id']} attempted to list administrators without admin privileges")
            return {
                "detail": {
                    "message": "You don't have permission to list administrators",
                    "status_code": 403
                }
            }
            
        return await self.user_use_cases.get_administrators(audit_data)
        
    async def get_professionals(self, request: Request, admin_id: str = None):
        """
        Retrieves professionals associated with an administrator.
        If admin_id not provided, uses the ID of the administrator from the token.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_professionals",
            "ip_address": request.client.host
        }
        
        current_user_profile = request.state.user.get("profile")
        current_user_id = request.state.user.get("user_id")
        
        if not admin_id and current_user_profile == "administrator":
            admin_id = current_user_id
        
        elif current_user_profile == "professional":
            admin_id = request.state.user.get("admin_id")
            if not admin_id:
                logger.warning(f"Professional {current_user_id} has no admin_id but attempted to get professionals")
                return {
                    "detail": {
                        "message": "You don't have permission to access this resource",
                        "status_code": 403
                    }
                }
        
        return await self.user_use_cases.get_professionals(admin_id, current_user_profile,audit_data)


    async def create_subscription(self, request: Request, subscription: CreateSubscriptions):
        """
        Creates a professional subscription.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "create_subscription",
            "ip_address": request.client.host
        }

        if request.state.user.get("profile") != "general_administrator":
            logger.warning(f"User {audit_data['user_id']} attempted to create subscription without admin privileges")
            return {
                "detail": {
                    "message": "Only general administrators can create subscriptions",
                    "status_code": 403
                }
            }
        
        return await self.user_use_cases.create_subscription(subscription, audit_data)
    

    async def get_subscriptions(self, request: Request):
        """
        Retrieves all existing subscriptions.
        """
        try:
            logger.info(f"Processing subscription listing request from {request.client.host}")
            await self.auth_middleware.verify_request(request)
            
            user_data = request.state.user if hasattr(request.state, 'user') else {}
            
            audit_data = {
                "user_id": user_data.get("user_id"),
                "profile": user_data.get("profile"),
                "action": "get_subscriptions",
                "ip_address": request.client.host
            }
            
            result = await self.user_use_cases.get_subscriptions(audit_data)
            return result
            
        except Exception as e:
            logger.error(f"Error in get_subscriptions controller: {str(e)}")
            raise
    

    async def get_subscription_by_id(self, request: Request, subscription_id: str):
        """
        Retrieves a professional's subscription by ID.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_subscription_by_id",
            "target_subscription_id": subscription_id,
            "ip_address": request.client.host
        }

        return await self.user_use_cases.get_subscription_by_id(subscription_id, audit_data)


    async def update_subscription(self, request: Request, subscription_id: str, subscription: CreateSubscriptions):
        """
        Updates an existing subscription.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "update_subscription",
            "ip_address": request.client.host
        }

        if request.state.user.get("profile") != "general_administrator":
            logger.warning(f"User {audit_data['user_id']} attempted to update subscription without admin privileges")
            return {
                "detail": {
                    "message": "Only general administrators can update subscriptions",
                    "status_code": 403
                }
            }
        
        return await self.user_use_cases.update_subscription(subscription_id, subscription, audit_data)
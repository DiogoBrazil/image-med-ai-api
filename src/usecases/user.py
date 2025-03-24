from fastapi import HTTPException
from ..utils.verify_email import is_email_valid
from ..utils.logger import get_logger
from ..adapters.token_adapter import TokenAdapter
from ..adapters.password_adapter import PasswordAdapter
from ..interfaces.login_user import LoginUser
from ..interfaces.create_user import CreateUser
from ..interfaces.update_user import UpdateUser
from ..repositories.user_repository import UserRepository
from ..utils.error_handler import raise_http_error
from src.config.settings import Settings


settings = Settings()
logger = get_logger(__name__)


class UserService:
    def __init__(self):
        self.user_repository = UserRepository()
        self.password_adapter = PasswordAdapter()
        self.token_adapter = TokenAdapter()
    
    async def add_user(self, user: CreateUser, audit_data=None):
       """Add a new user after validating their data."""
       try:
           
           user_data = user.dict()
           
           # Validação de campos obrigatórios
           required_fields = ["full_name", "email", "password", "profile"]
           for field in required_fields:
               if field not in user_data or not user_data[field]:
                   logger.error(f"Error adding user: {field} cannot be empty")
                   raise_http_error(400, f"Error adding user: {field} cannot be empty")
           
           # Validação do perfil
           valid_profiles = ["administrator", "professional"]
           if user_data["profile"] not in valid_profiles:
               logger.error(f"Error adding user: Invalid profile")
               raise_http_error(422, f"Invalid profile. Should be one of: {', '.join(valid_profiles)}")
           
           # Validação do campo status
           if "status" in user_data and user_data["status"] not in ["active", "inactive"]:
               logger.error(f"Error adding user: Invalid status")
               raise_http_error(422, "Invalid status. Should be 'active' or 'inactive'")
           
           # Validação de email
           if not is_email_valid(user_data["email"]):
               logger.error(f"Error adding user: Invalid email")
               raise_http_error(422, "Invalid email format")
           
           # Verifica se o usuário já existe
           user_exists = await self.user_repository.get_user_by_email(user_data["email"])
           if user_exists:
               logger.error("Error adding user: User already exists")
               raise_http_error(409, "User with this email already exists")
           
           # Hash da senha
           user_data["password_hash"] = await self.password_adapter.hash_password(user_data["password"])
           
           # Inserir o usuário
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
            
            # Buscar usuário pelo email
            user_info = await self.user_repository.get_user_by_email(email)
            
            if not user_info:
                logger.error(f"Login attempt failed: User {email} not found")
                raise_http_error(404, "User not found")

            if user_info["status"] != "active":
                logger.error(f"Login attempt failed: User {email} is inactive")
                raise_http_error(403, "User account is inactive")

            # Verificar senha
            if not await self.password_adapter.verify_password(
                user_login["password"], user_info["password_hash"]
            ):
                logger.error(f"Login attempt failed: Incorrect password for {email}")
                raise_http_error(401, "Incorrect password")

            # Criar token JWT
            token = await self.token_adapter.create_token(
                user_info["id"],
                user_info["full_name"],
                email,
                user_info["profile"],
                user_info.get("admin_id")  # Passa o admin_id se o usuário for um profissional
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

            # Remove senha do resultado
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
                # Remove senha do resultado
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
    
    async def update_user(self, user_id: str, user: UpdateUser, audit_data=None):
        """Update user information."""
        try:
            # Verificar se o usuário existe
            existing_user = await self.user_repository.get_user_by_id(user_id)
            if not existing_user:
                logger.error(f"Error updating user: User with ID {user_id} not found")
                raise_http_error(404, "User not found")

            # Extrair dados da atualização
            user_data = user.dict(exclude_unset=True)
            
            # Validar email se for atualizado
            if "email" in user_data and not is_email_valid(user_data["email"]):
                logger.error("Error updating user: Invalid email format")
                raise_http_error(422, "Invalid email format")
                
            # Validar perfil se for atualizado
            if "profile" in user_data:
                valid_profiles = ["administrator", "professional"]
                if user_data["profile"] not in valid_profiles:
                    logger.error("Error updating user: Invalid profile")
                    raise_http_error(422, f"Invalid profile. Should be one of: {', '.join(valid_profiles)}")
            
            # Validar status se for atualizado
            if "status" in user_data and user_data["status"] not in ["active", "inactive"]:
                logger.error("Error updating user: Invalid status")
                raise_http_error(422, "Invalid status. Should be 'active' or 'inactive'")
                
            # Se a senha for atualizada, fazer o hash
            if "password_hash" in user_data:
                user_data["password_hash"] = await self.password_adapter.hash_password(user_data["password_hash"])

            # Atualizar usuário
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

    async def delete_user(self, user_id: str, audit_data=None):
        """Delete a user by ID."""
        try:

            # Verificar se o usuário existe
            existing_user = await self.user_repository.get_user_by_id(user_id)
            if not existing_user:
                logger.error(f"Error deleting user: User with ID {user_id} not found")
                raise_http_error(404, "User not found")

            # Deletar usuário
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
            
    async def get_professionals(self, admin_id: str, audit_data=None):
        """Retrieve all professionals associated with an administrator."""
        try:
            # Verificar se o administrador existe
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
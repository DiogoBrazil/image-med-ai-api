from src.repositories.user_repository import UserRepository
from src.adapters.password_adapter import PasswordAdapter
from src.config.settings import Settings
from src.utils.logger import get_logger
import asyncpg
from fastapi import HTTPException
from ..utils.error_handler import raise_http_error

async def ensure_root_user():
    """
    Checks if the root administrator user exists.
    If not, creates it with the data defined in the environment variables.
    
    Returns:
        dict: Operation status with result message
    
    Raises:
        HTTPException: In case of critical errors that prevent application startup
    """
    
    logger = get_logger("root_user_setup")
    settings = Settings()
    user_repo = UserRepository()
    password_adapter = PasswordAdapter()
    
    try:

        logger.info("Testing database connection...")
        try:

            db_url = settings.POSTGRES_URL
            db_info = db_url.split("@")[-1] if "@" in db_url else db_url
            logger.info(f"Trying to connect to: {db_info}")
            

            conn = await asyncpg.connect(settings.POSTGRES_URL)
            await conn.close()
            logger.info("Database connection established successfully")
        except Exception as conn_err:
            error_msg = f"Error connecting to database: {str(conn_err)}"
            logger.error(error_msg)
            logger.error(f"Check if the database URL is correct: {settings.POSTGRES_URL}")
            raise_http_error(500, error_msg)
        

        try:
            await user_repo.init_pool()
        except Exception as pool_err:
            error_msg = f"Error initializing connection pool: {str(pool_err)}"
            logger.error(error_msg)
            raise_http_error(500, error_msg)
        

        try:
            existing_user = await user_repo.get_user_by_email(settings.USER_EMAIL_ROOT)
            
            if existing_user:
                logger.info(f"Root administrator user already exists: {settings.USER_EMAIL_ROOT}")
                return {
                    "status": "Error",
                    "message": f"Root administrator user already exists",
                    "status_code": 403
                }
        except Exception as user_check_err:
            error_msg = f"Error checking existing user: {str(user_check_err)}"
            logger.error(error_msg)
            raise_http_error(500, error_msg)
        

        valid_profiles = ["general_administrator", "administrator", "professional"]
        if settings.USER_ROOT_PROFILE not in valid_profiles:
            error_msg = f"Invalid profile: {settings.USER_ROOT_PROFILE}. Valid profiles: {', '.join(valid_profiles)}"
            logger.error(error_msg)
            raise_http_error(400, error_msg)
        

        logger.info(f"Creating root administrator user: {settings.USER_EMAIL_ROOT}")
        
        try:

            hashed_password = await password_adapter.hash_password(settings.USER_ROOT_PASSWORD)
            

            user_data = {
                "full_name": settings.USER_NAME_ROOT,
                "email": settings.USER_EMAIL_ROOT,
                "password_hash": hashed_password,
                "profile": settings.USER_ROOT_PROFILE,
                "admin_id": None,
                "status": settings.USER_STATUS_ROOT
            }
            

            result = await user_repo.add_user(user_data)
            
            if result["added"]:
                success_msg = f"Root administrator user created successfully: {result['user_id']}"
                logger.info(success_msg)
                return {
                    "status": "success",
                    "message": success_msg,
                    "user_id": result["user_id"]
                }
            else:
                error_msg = "Failed to create root administrator user"
                logger.error(error_msg)
                raise_http_error(500, error_msg)
        except HTTPException as http_exc:

            raise http_exc
        except Exception as user_create_err:
            error_msg = f"Error creating root user: {str(user_create_err)}"
            logger.error(error_msg)
            raise_http_error(500, error_msg)
    
    except HTTPException:

        raise
    except Exception as e:

        error_msg = f"Unexpected error checking/creating root administrator user: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        raise_http_error(500, error_msg)
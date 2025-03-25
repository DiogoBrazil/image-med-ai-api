from datetime import datetime
import asyncpg
import uuid
from typing import Any, Dict, List, Optional
from ..utils.logger import get_logger
from ..db.database import get_database
from ..config.settings import Settings

settings = Settings()
logger = get_logger(__name__)

class UserRepository:
    def __init__(self):
        self.db_connection = get_database()
        self.pool = None

    async def init_pool(self):
        """Initialize the connection pool if necessary."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(dsn=self.db_connection, min_size=1, max_size=10)
            logger.info("Connection pool initialized.")

    async def add_user(self, user_data: Dict) -> Dict:
        """Add a new user."""
        await self.init_pool()
        try:
            async with self.pool.acquire() as conn:
                query = """
                    INSERT INTO users (full_name, email, password_hash, profile, admin_id, status)
                    VALUES ($1, $2, $3, $4, $5, $6) RETURNING id
                """
                admin_id = user_data.get("admin_id")
                

                if admin_id and isinstance(admin_id, str):
                    try:
                        admin_id = uuid.UUID(admin_id)
                    except ValueError:
                        logger.error(f"Invalid UUID format for admin_id: {admin_id}")
                        return {"user_id": "", "added": False}

                returned_id = await conn.fetchval(
                    query,
                    user_data["full_name"],
                    user_data["email"],
                    user_data["password_hash"],
                    user_data["profile"],
                    admin_id,
                    user_data.get("status", "active")
                )
                logger.info(f"User {user_data['email']} added with ID {returned_id}")
                return {
                    "user_id": str(returned_id),
                    "added": True
                }
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return {
                "user_id": "",
                "added": False
            }

    async def login_user(self, email: str) -> Optional[Dict]:
        """Retrieve user data by email for login."""
        await self.init_pool()
        try:
            async with self.pool.acquire() as conn:
                query = "SELECT * FROM users WHERE email = $1"
                user = await conn.fetchrow(query, email)
                if user:
                    logger.info(f"User {email} found for login")
                    return {
                        "id": str(user["id"]),
                        "full_name": user["full_name"],
                        "email": user["email"],
                        "password_hash": user["password_hash"],
                        "profile": user["profile"],
                        "admin_id": str(user["admin_id"]) if user["admin_id"] else None,
                        "status": user["status"],
                        "created_at": user["created_at"]
                    }
                else:
                    logger.info(f"User {email} not found for login")
                    return None
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return None
        
    async def get_users(self, admin_id: Optional[str] = None) -> List[Dict]:
        """
        Retrieve all users. 
        If admin_id is provided, return only users associated with that admin.
        """
        await self.init_pool()
        try:
            async with self.pool.acquire() as conn:
                if admin_id:
                    try:
                        admin_uuid = uuid.UUID(admin_id)
                        query = "SELECT * FROM users WHERE admin_id = $1 OR id = $1"
                        users = await conn.fetch(query, admin_uuid)
                    except ValueError:
                        logger.error(f"Invalid UUID format for admin_id: {admin_id}")
                        return []
                else:
                    query = "SELECT * FROM users"
                    users = await conn.fetch(query)
                
                logger.info(f"Found {len(users)} users")
                return [
                    {
                        "id": str(user["id"]),
                        "full_name": user["full_name"],
                        "email": user["email"],
                        "profile": user["profile"],
                        "admin_id": str(user["admin_id"]) if user["admin_id"] else None,
                        "status": user["status"],
                        "created_at": user["created_at"]
                    }
                    for user in users
                ]
        except Exception as e:
            logger.error(f"Error fetching users: {e}")
            return []
        
    async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Retrieve a user by ID."""
        await self.init_pool()
        try:
            user_uuid = uuid.UUID(user_id)
            async with self.pool.acquire() as conn:
                query = "SELECT * FROM users WHERE id = $1"
                user = await conn.fetchrow(query, user_uuid)
                if user:
                    logger.info(f"User {user_id} found")
                    return {
                        "id": str(user["id"]),
                        "full_name": user["full_name"],
                        "email": user["email"],
                        "profile": user["profile"],
                        "password_hash": user["password_hash"],
                        "admin_id": str(user["admin_id"]) if user["admin_id"] else None,
                        "status": user["status"],
                        "created_at": user["created_at"]
                    }
                else:
                    logger.info(f"User {user_id} not found")
                    return None
        except ValueError:
            logger.error(f"Invalid UUID format: {user_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching user by ID: {e}")
            return None
        
    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Retrieve a user by email."""
        await self.init_pool()
        try:
            async with self.pool.acquire() as conn:
                query = "SELECT * FROM users WHERE email = $1"
                user = await conn.fetchrow(query, email)
                if user:
                    logger.info(f"User {email} found")
                    return {
                        "id": str(user["id"]),
                        "full_name": user["full_name"],
                        "email": user["email"],
                        "password_hash": user["password_hash"],
                        "profile": user["profile"],
                        "admin_id": str(user["admin_id"]) if user["admin_id"] else None,
                        "status": user["status"],
                        "created_at": user["created_at"]
                    }
                else:
                    logger.info(f"User {email} not found")
                    return None
        except Exception as e:
            logger.error(f"Error fetching user by email: {e}")
            return None
        
    async def update_user(self, user_id: str, user_data: Dict) -> Dict:
        """Update user information."""
        await self.init_pool()
        try:
            user_uuid = uuid.UUID(user_id)
            admin_id = user_data.get("admin_id")
            

            if admin_id and isinstance(admin_id, str):
                try:
                    admin_id = uuid.UUID(admin_id)
                except ValueError:
                    logger.error(f"Invalid UUID format for admin_id: {admin_id}")
                    return {"user_id": "", "updated": False}
                    
            async with self.pool.acquire() as conn:
                query = """
                    UPDATE users
                    SET full_name = $1, email = $2, profile = $3, admin_id = $4, status = $5
                    WHERE id = $6 RETURNING id
                """
                updated_id = await conn.fetchval(
                    query,
                    user_data["full_name"],
                    user_data["email"],
                    user_data["profile"],
                    admin_id,
                    user_data.get("status", "active"),
                    user_uuid
                )
                if updated_id:
                    logger.info(f"User {user_id} updated")
                    return {
                        "user_id": user_id,
                        "updated": True,
                    }
                else:
                    logger.info(f"User {user_id} not found for update")
                    return {
                        "user_id": "",
                        "updated": False,
                    }
        except ValueError:
            logger.error(f"Invalid UUID format: {user_id}")
            return {"user_id": "", "updated": False}
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return {
                "user_id": "",
                "updated": False,
            }
        
    async def update_password(self, user_id: str, password_hash: str) -> Dict:
        """Update user's password."""
        await self.init_pool()
        try:
            user_uuid = uuid.UUID(user_id)
            async with self.pool.acquire() as conn:
                query = """
                    UPDATE users
                    SET password_hash = $1
                    WHERE id = $2 RETURNING id
                """
                updated_id = await conn.fetchval(query, password_hash, user_uuid)
                if updated_id:
                    logger.info(f"Password updated for user {user_id}")
                    return {
                        "user_id": user_id,
                        "updated": True,
                    }
                else:
                    logger.info(f"User {user_id} not found for password update")
                    return {
                        "user_id": "",
                        "updated": False,
                    }
        except ValueError:
            logger.error(f"Invalid UUID format: {user_id}")
            return {"user_id": "", "updated": False}
        except Exception as e:
            logger.error(f"Error updating password: {e}")
            return {
                "user_id": "",
                "updated": False,
            }
        
    async def delete_user(self, user_id: str) -> Dict:
        """Delete a user by ID."""
        await self.init_pool()
        try:
            user_uuid = uuid.UUID(user_id)
            async with self.pool.acquire() as conn:
                query = "DELETE FROM users WHERE id = $1 RETURNING id"
                deleted_id = await conn.fetchval(query, user_uuid)
                if deleted_id:
                    logger.info(f"User {user_id} deleted successfully")
                    return {
                        "user_id": user_id,
                        "deleted": True,
                    }
                else:
                    logger.info(f"User with ID {user_id} not found for deletion")
                    return {
                        "user_id": "",
                        "deleted": False,
                    }
        except ValueError:
            logger.error(f"Invalid UUID format: {user_id}")
            return {"user_id": "", "deleted": False}
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return {
                "user_id": "",
                "deleted": False,
            }
            
    async def get_administrators(self) -> List[Dict]:
        """Retrieve all users with administrator profile."""
        await self.init_pool()
        try:
            async with self.pool.acquire() as conn:
                query = "SELECT * FROM users WHERE profile = 'administrator'"
                users = await conn.fetch(query)
                logger.info(f"Found {len(users)} administrators")
                return [
                    {
                        "id": str(user["id"]),
                        "full_name": user["full_name"],
                        "email": user["email"],
                        "profile": user["profile"],
                        "status": user["status"],
                        "created_at": user["created_at"]
                    }
                    for user in users
                ]
        except Exception as e:
            logger.error(f"Error fetching administrators: {e}")
            return []
    
    async def get_professionals(self) -> List[Dict]:
        """Retrieve all users with professionals profile."""
        await self.init_pool()
        try:
            async with self.pool.acquire() as conn:
                query = "SELECT * FROM users WHERE profile = 'professional'"
                users = await conn.fetch(query)
                logger.info(f"Found {len(users)} professionals")
                return [
                    {
                        "id": str(user["id"]),
                        "full_name": user["full_name"],
                        "email": user["email"],
                        "profile": user["profile"],
                        "status": user["status"],
                        "created_at": user["created_at"]
                    }
                    for user in users
                ]
        except Exception as e:
            logger.error(f"Error fetching professionals: {e}")
            return []
            
    async def get_professionals_by_admin(self, admin_id: str) -> List[Dict]:
        """Retrieve all professionals associated with a specific admin."""
        await self.init_pool()
        try:
            admin_uuid = uuid.UUID(admin_id)
            async with self.pool.acquire() as conn:
                query = "SELECT * FROM users WHERE admin_id = $1 AND profile = 'professional'"
                users = await conn.fetch(query, admin_uuid)
                logger.info(f"Found {len(users)} professionals for admin {admin_id}")
                return [
                    {
                        "id": str(user["id"]),
                        "full_name": user["full_name"],
                        "email": user["email"],
                        "profile": user["profile"],
                        "status": user["status"],
                        "created_at": user["created_at"]
                    }
                    for user in users
                ]
        except ValueError:
            logger.error(f"Invalid UUID format: {admin_id}")
            return []
        except Exception as e:
            logger.error(f"Error fetching professionals: {e}")
            return []
        
    
    async def create_subscription(self, subscription_data: Dict) -> Dict:
        """Create a new subscription for a professional."""
        await self.init_pool()
        try:
            async with self.pool.acquire() as conn:
                query = """
                    INSERT INTO subscriptions (admin_id, start_date, end_date, status)
                    VALUES ($1, $2, $3, $4) RETURNING id
                """
                admin_id = subscription_data.get("admin_id")
                start_date = subscription_data.get("start_date")
                end_date = subscription_data.get("end_date")
                status = subscription_data.get("status", "active")
                

                if admin_id and isinstance(admin_id, str):
                    try:
                        admin_id = uuid.UUID(admin_id)
                    except ValueError:
                        logger.error(f"Invalid UUID format for admin_id: {admin_id}")
                        return {"subscription_id": "", "added": False}
                
                returned_id = await conn.fetchval(
                    query,
                    admin_id,
                    start_date,
                    end_date,
                    status
                )
                logger.info(f"Subscription added with ID {returned_id}")
                return {
                    "subscription_id": str(returned_id),
                    "added": True
                }
        except Exception as e:
            logger.error(f"Error adding subscription: {e}")
            return {
                "subscription_id": "",
                "added": False
            }
    
    async def get_subscriptions(self, user_id: str = None) -> List[Dict]:
        """
        Retrieve all subscriptions or subscriptions for a specific user.
        
        If user_id is provided, it will check if the user exists before returning subscriptions.
        This is to handle the case where a user tries to access subscriptions.
        """
        await self.init_pool()
        try:
            async with self.pool.acquire() as conn:
                if user_id:
                    try:
                        user_uuid = uuid.UUID(user_id)
                        
                        user_query = "SELECT id, full_name, profile FROM users WHERE id = $1"
                        user = await conn.fetchrow(user_query, user_uuid)
                        
                        if not user:
                            logger.warning(f"User with ID {user_id} not found when accessing subscriptions")
                            raise ValueError("User not found")
                    except ValueError as e:
                        logger.error(f"Invalid user ID or user not found: {e}")
                        raise ValueError("User not found")
                
                query = "SELECT * FROM subscriptions"
                subscriptions = await conn.fetch(query)
                
                logger.info(f"Found {len(subscriptions)} subscriptions")
                
                return [
                    {
                        "id": str(subscription["id"]),
                        "admin_id": str(subscription["admin_id"]),
                        "start_date": subscription["start_date"],
                        "end_date": subscription["end_date"],
                        "status": subscription["status"]
                    }
                    for subscription in subscriptions
                ]
        except ValueError as e:
            logger.error(f"Error validating user for subscriptions: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching subscriptions: {e}")
            return []

    
    async def get_subscription_by_admin_id(self, admin_id: str) -> Optional[Dict]:
        """Retrieve subscription data by admin ID."""
        await self.init_pool()
        try:
            admin_uuid = uuid.UUID(admin_id)
            async with self.pool.acquire() as conn:
                query = "SELECT * FROM subscriptions WHERE admin_id = $1"
                subscription = await conn.fetchrow(query, admin_uuid)
                if subscription:
                    logger.info(f"Subscription found for admin {admin_id}")
                    return {
                        "id": str(subscription["id"]),
                        "admin_id": str(subscription["admin_id"]),
                        "start_date": subscription["start_date"],
                        "end_date": subscription["end_date"],
                        "status": subscription["status"]
                    }
                else:
                    logger.info(f"No subscription found for admin {admin_id}")
                    return None
        except ValueError:
            logger.error(f"Invalid UUID format: {admin_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching subscription: {e}")
            return None
    

    async def get_subscription_by_id(self, subscription_id: str) -> Optional[Dict]:
        """Retrieve subscription data by ID."""
        await self.init_pool()
        try:
            subscription_uuid = uuid.UUID(subscription_id)
            async with self.pool.acquire() as conn:

                user_check = "SELECT COUNT(*) FROM users"
                user_count = await conn.fetchval(user_check)
                if user_count == 0:
                    logger.warning("No users found in database when accessing subscription by ID")
                    raise ValueError("User not found")
                

                query = "SELECT * FROM subscriptions WHERE id = $1"
                subscription = await conn.fetchrow(query, subscription_uuid)
                if subscription:
                    logger.info(f"Subscription found for ID {subscription_id}")
                    return {
                        "id": str(subscription["id"]),
                        "admin_id": str(subscription["admin_id"]),
                        "start_date": subscription["start_date"],
                        "end_date": subscription["end_date"],
                        "status": subscription["status"]
                    }
                else:
                    logger.info(f"No subscription found for ID {subscription_id}")
                    return None
        except ValueError as e:
            if str(e) == "User not found":
                raise
            logger.error(f"Invalid UUID format: {subscription_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching subscription: {e}")
            return None
    

    async def update_subscription(self, subscription_id: str, subscription_data: Dict) -> Dict:
        """Update subscription information."""
        await self.init_pool()
        try:
            subscription_uuid = uuid.UUID(subscription_id)
            admin_id = subscription_data.get("admin_id")
            start_date = subscription_data.get("start_date")
            end_date = subscription_data.get("end_date")
            status = subscription_data.get("status", "active")
            

            if admin_id and isinstance(admin_id, str):
                try:
                    admin_id = uuid.UUID(admin_id)
                except ValueError:
                    logger.error(f"Invalid UUID format for admin_id: {admin_id}")
                    return {"subscription_id": "", "updated": False}
                    
            async with self.pool.acquire() as conn:
                query = """
                    UPDATE subscriptions
                    SET admin_id = $1, start_date = $2, end_date = $3, status = $4
                    WHERE id = $5 RETURNING id
                """
                updated_id = await conn.fetchval(
                    query,
                    admin_id,
                    start_date,
                    end_date,
                    status,
                    subscription_uuid
                )
                if updated_id:
                    logger.info(f"Subscription {subscription_id} updated")
                    return {
                        "subscription_id": subscription_id,
                        "updated": True,
                    }
                else:
                    logger.info(f"Subscription {subscription_id} not found for update")
                    return {
                        "subscription_id": "",
                        "updated": False,
                    }
        except ValueError:
            logger.error(f"Invalid UUID format: {subscription_id}")
            return {"subscription_id": "", "updated": False}
        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            return {
                "subscription_id": "",
                "updated": False,
            }
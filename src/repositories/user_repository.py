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
                
                # Convert string to UUID if admin_id exists
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
            
            # Convert string to UUID if admin_id exists
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
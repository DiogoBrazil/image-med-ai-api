from datetime import datetime
import asyncpg
import uuid
from typing import Any, Dict, List, Optional
from ..utils.logger import get_logger
from ..db.database import get_database
from ..config.settings import Settings

settings = Settings()
logger = get_logger(__name__)

class HealthUnitRepository:
    def __init__(self):
        self.db_connection = get_database()
        self.pool = None

    async def init_pool(self):
        """Initialize the connection pool if necessary."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(dsn=self.db_connection, min_size=1, max_size=10)
            logger.info("Connection pool initialized.")

    async def add_health_unit(self, unit_data: Dict) -> Dict:
        """Add a new health unit."""
        await self.init_pool()
        try:

            admin_id = unit_data.get("admin_id")
            if admin_id and isinstance(admin_id, str):
                try:
                    admin_id = uuid.UUID(admin_id)
                except ValueError:
                    logger.error(f"Invalid UUID format for admin_id: {admin_id}")
                    return {"unit_id": "", "added": False}
            
            async with self.pool.acquire() as conn:
                query = """
                    INSERT INTO health_units (admin_id, name, cnpj, status)
                    VALUES ($1, $2, $3, $4) RETURNING id
                """
                returned_id = await conn.fetchval(
                    query,
                    admin_id,
                    unit_data["name"],
                    unit_data.get("cnpj"),
                    unit_data.get("status", "active")
                )
                logger.info(f"Health unit {unit_data['name']} added with ID {returned_id}")
                return {
                    "unit_id": str(returned_id),
                    "added": True
                }
        except Exception as e:
            logger.error(f"Error adding health unit: {e}")
            return {
                "unit_id": "",
                "added": False
            }

    async def get_health_units(self, admin_id: Optional[str] = None) -> List[Dict]:
        """
        Retrieve all health units.
        If admin_id is provided, return only units associated with that admin.
        """
        await self.init_pool()
        try:
            async with self.pool.acquire() as conn:
                if admin_id:
                    try:
                        admin_uuid = uuid.UUID(admin_id)
                        query = "SELECT * FROM health_units WHERE admin_id = $1"
                        units = await conn.fetch(query, admin_uuid)
                    except ValueError:
                        logger.error(f"Invalid UUID format for admin_id: {admin_id}")
                        return []
                else:
                    query = "SELECT * FROM health_units"
                    units = await conn.fetch(query)
                
                logger.info(f"Found {len(units)} health units")
                return [
                    {
                        "id": str(unit["id"]),
                        "admin_id": str(unit["admin_id"]),
                        "name": unit["name"],
                        "cnpj": unit["cnpj"],
                        "created_at": unit["created_at"],
                        "status": unit["status"]
                    }
                    for unit in units
                ]
        except Exception as e:
            logger.error(f"Error fetching health units: {e}")
            return []
        
    async def get_health_unit_by_id(self, unit_id: str) -> Optional[Dict]:
        """Retrieve a health unit by ID."""
        await self.init_pool()
        try:
            unit_uuid = uuid.UUID(unit_id)
            async with self.pool.acquire() as conn:
                query = "SELECT * FROM health_units WHERE id = $1"
                unit = await conn.fetchrow(query, unit_uuid)
                if unit:
                    logger.info(f"Health unit {unit_id} found")
                    return {
                        "id": str(unit["id"]),
                        "admin_id": str(unit["admin_id"]),
                        "name": unit["name"],
                        "cnpj": unit["cnpj"],
                        "created_at": unit["created_at"],
                        "status": unit["status"]
                    }
                else:
                    logger.info(f"Health unit {unit_id} not found")
                    return None
        except ValueError:
            logger.error(f"Invalid UUID format: {unit_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching health unit by ID: {e}")
            return None
        
    async def update_health_unit(self, unit_id: str, unit_data: Dict) -> Dict:
        """Update health unit information."""
        await self.init_pool()
        try:
            unit_uuid = uuid.UUID(unit_id)

            admin_id = unit_data.get("admin_id")
            if admin_id and isinstance(admin_id, str):
                try:
                    admin_id = uuid.UUID(admin_id)
                except ValueError:
                    logger.error(f"Invalid UUID format for admin_id: {admin_id}")
                    return {"unit_id": "", "updated": False}
                    
            async with self.pool.acquire() as conn:
                query = """
                    UPDATE health_units
                    SET name = $1, cnpj = $2, status = $3
                    WHERE id = $4 RETURNING id
                """
                updated_id = await conn.fetchval(
                    query,
                    unit_data["name"],
                    unit_data.get("cnpj"),
                    unit_data.get("status", "active"),
                    unit_uuid
                )
                if updated_id:
                    logger.info(f"Health unit {unit_id} updated")
                    return {
                        "unit_id": unit_id,
                        "updated": True,
                    }
                else:
                    logger.info(f"Health unit {unit_id} not found for update")
                    return {
                        "unit_id": "",
                        "updated": False,
                    }
        except ValueError:
            logger.error(f"Invalid UUID format: {unit_id}")
            return {"unit_id": "", "updated": False}
        except Exception as e:
            logger.error(f"Error updating health unit: {e}")
            return {
                "unit_id": "",
                "updated": False,
            }
        
    async def delete_health_unit(self, unit_id: str) -> Dict:
        """Delete a health unit by ID."""
        await self.init_pool()
        try:
            unit_uuid = uuid.UUID(unit_id)
            async with self.pool.acquire() as conn:

                check_query = "SELECT COUNT(*) FROM professional_assignments WHERE health_unit_id = $1"
                count = await conn.fetchval(check_query, unit_uuid)
                
                if count > 0:
                    logger.warning(f"Cannot delete health unit {unit_id} - has {count} professional assignments")
                    return {
                        "unit_id": unit_id,
                        "deleted": False,
                        "reason": "Unit has professional assignments"
                    }
                

                check_query = "SELECT COUNT(*) FROM attendances WHERE health_unit_id = $1"
                count = await conn.fetchval(check_query, unit_uuid)
                
                if count > 0:
                    logger.warning(f"Cannot delete health unit {unit_id} - has {count} attendances")
                    return {
                        "unit_id": unit_id,
                        "deleted": False,
                        "reason": "Unit has attendances"
                    }
                

                delete_query = "DELETE FROM health_units WHERE id = $1 RETURNING id"
                deleted_id = await conn.fetchval(delete_query, unit_uuid)
                
                if deleted_id:
                    logger.info(f"Health unit {unit_id} deleted successfully")
                    return {
                        "unit_id": unit_id,
                        "deleted": True,
                    }
                else:
                    logger.info(f"Health unit with ID {unit_id} not found for deletion")
                    return {
                        "unit_id": "",
                        "deleted": False,
                        "reason": "Unit not found"
                    }
        except ValueError:
            logger.error(f"Invalid UUID format: {unit_id}")
            return {"unit_id": "", "deleted": False, "reason": "Invalid UUID format"}
        except Exception as e:
            logger.error(f"Error deleting health unit: {e}")
            return {
                "unit_id": "",
                "deleted": False,
                "reason": str(e)
            }
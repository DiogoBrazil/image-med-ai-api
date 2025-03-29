from fastapi import HTTPException
from ..utils.logger import get_logger
from ..interfaces.create_health_unit import CreateHealthUnit
from ..interfaces.update_health_unit import UpdateHealthUnit
from ..repositories.health_unit_repository import HealthUnitRepository
from ..repositories.user_repository import UserRepository
from ..utils.error_handler import raise_http_error
from src.config.settings import Settings

settings = Settings()
logger = get_logger(__name__)

class HealthUnitUseCases:
    def __init__(self):
        self.health_unit_repository = HealthUnitRepository()
        self.user_repository = UserRepository()
    
    async def add_health_unit(self, health_unit: CreateHealthUnit, audit_data=None):
        """Add a new health unit after validating the data."""
        try:

            unit_data = health_unit.dict()

            admin = await self.user_repository.get_user_by_id(unit_data.get("admin_id"))
            if not admin:
                logger.error(f"Error adding health unit: Admin with ID {unit_data.get('admin_id')} not found")
                raise_http_error(404, "Administrator not found")
                        
            if not unit_data.get("name"):
                logger.error("Error adding health unit: Name cannot be empty")
                raise_http_error(400, "Health unit name cannot be empty")
                
            if not unit_data.get("cnpj"):
                logger.error("Error adding health unit: CNPJ cannot be empty")
                raise_http_error(400, "CNPJ cannot be empty")

            if "status" in unit_data and unit_data["status"] not in ["active", "inactive"]:
                logger.error("Error adding health unit: Invalid status")
                raise_http_error(422, "Invalid status. Should be 'active' or 'inactive'")        

            result = await self.health_unit_repository.add_health_unit(unit_data)
            
            if result["added"]:
                return {
                    "detail": {
                        "message": "Health unit added successfully",
                        "unit_id": result["unit_id"],
                        "status_code": 201
                    }
                }
            else:
                logger.error("Error adding health unit")
                raise_http_error(500, "Error adding health unit to database")
                
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Unexpected error when adding health unit: {e}")
            raise_http_error(500, "Unexpected error when adding health unit")

    
    async def get_health_units(self, audit_data=None,  admin_id: str = None):
        """
        Retrieve all health units or units associated with an admin.
        If admin_id is provided, return only units associated with that admin.
        """
        try:
            if admin_id:
                admin = await self.user_repository.get_user_by_id(admin_id)
                if not admin:
                    logger.error(f"Error retrieving health units: Admin with ID {admin_id} not found")
                    raise_http_error(404, "Administrator not found")
            

            units = await self.health_unit_repository.get_health_units(admin_id)
            return {
                "detail": {
                    "message": "Health units retrieved successfully",
                    "health_units": units,
                    "count": len(units),
                    "status_code": 200
                }
            }
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error retrieving health units: {e}")
            raise_http_error(500, "Error retrieving health units")
    

    async def get_health_unit_by_id(self, unit_id: str, audit_data=None):
        """Retrieve a health unit by ID."""
        try:
            unit = await self.health_unit_repository.get_health_unit_by_id(unit_id)
            
            if unit:
                return {
                    "detail": {
                        "message": "Health unit retrieved successfully",
                        "health_unit": unit,
                        "status_code": 200
                    }
                }
            else:
                logger.error(f"Health unit with ID {unit_id} not found")
                raise_http_error(404, "Health unit not found")
                
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error retrieving health unit: {e}")
            raise_http_error(500, "Error retrieving health unit")
    
    async def update_health_unit(self, unit_id: str, health_unit: UpdateHealthUnit, audit_data=None):
        """Update health unit information."""
        try:

            existing_unit = await self.health_unit_repository.get_health_unit_by_id(unit_id)
            if not existing_unit:
                logger.error(f"Error updating health unit: Unit with ID {unit_id} not found")
                raise_http_error(404, "Health unit not found")
            

            unit_data = health_unit.dict(exclude_unset=True)
            
            
            if "name" in unit_data and not unit_data["name"]:
                logger.error("Error updating health unit: Name cannot be empty")
                raise_http_error(400, "Health unit name cannot be empty")
                
            if "status" in unit_data and unit_data["status"] not in ["active", "inactive"]:
                logger.error("Error updating health unit: Invalid status")
                raise_http_error(422, "Invalid status. Should be 'active' or 'inactive'")
            

            result = await self.health_unit_repository.update_health_unit(unit_id, unit_data)
            
            if result["updated"]:
                return {
                    "detail": {
                        "message": "Health unit updated successfully",
                        "unit_id": unit_id,
                        "status_code": 200
                    }
                }
            else:
                logger.error(f"Failed to update health unit with ID {unit_id}")
                raise_http_error(500, "Failed to update health unit")
                
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error updating health unit: {e}")
            raise_http_error(500, "Error updating health unit")

    
    async def delete_health_unit(self, unit_id: str, audit_data=None):
        """Delete a health unit by ID."""
        try:
            existing_unit = await self.health_unit_repository.get_health_unit_by_id(unit_id)
            if not existing_unit:
                logger.error(f"Error deleting health unit: Unit with ID {unit_id} not found")
                raise_http_error(404, "Health unit not found")
            
            if audit_data and audit_data.get("user_id") and audit_data.get("profile") == "administrator":
                admin_id = audit_data.get("user_id")
                
                admin_units = await self.health_unit_repository.get_health_units(admin_id)
                
                unit_belongs_to_admin = False
                for unit in admin_units:
                    if unit.get("id") == unit_id:
                        unit_belongs_to_admin = True
                        break
                
                if not unit_belongs_to_admin:
                    logger.error(f"Administrator {admin_id} attempted to delete health unit {unit_id} that does not belong to them")
                    raise_http_error(403, "You can only delete health units that belong to your account")

            result = await self.health_unit_repository.delete_health_unit(unit_id)
            
            if result["deleted"]:
                logger.info(f"Health unit with ID {unit_id} deleted successfully")
                return {
                    "detail": {
                        "message": "Health unit deleted successfully",
                        "unit_id": unit_id,
                        "status_code": 200
                    }
                }
            else:
                if "reason" in result:
                    logger.error(f"Failed to delete health unit with ID {unit_id}: {result['reason']}")
                    raise_http_error(409, f"Cannot delete health unit: {result['reason']}")
                else:
                    logger.error(f"Failed to delete health unit with ID {unit_id}")
                    raise_http_error(500, "Failed to delete health unit")
                
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error deleting health unit: {e}")
            raise_http_error(500, "Error deleting health unit")
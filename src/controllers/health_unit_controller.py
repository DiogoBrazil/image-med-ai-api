from fastapi import Request
from ..interfaces.create_health_unit import CreateHealthUnit
from ..interfaces.update_health_unit import UpdateHealthUnit
from ..usecases.health_unit_usecases import HealthUnitUseCases
from ..utils.credentials_middleware import AuthMiddleware
from ..utils.logger import get_logger

logger = get_logger(__name__)

class HealthUnitController:
    def __init__(self):
        self.health_unit_use_cases = HealthUnitUseCases()
        self.auth_middleware = AuthMiddleware()
    
    async def add_health_unit(self, request: Request, health_unit: CreateHealthUnit):
        """
        Adds a new health unit.
        Requires administrator profile.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "add_health_unit",
            "ip_address": request.client.host
        }
        
        if request.state.user.get("profile") != "administrator" and request.state.user.get("profile") != "general_administrator":
            logger.warning(f"User {audit_data['user_id']} attempted to add health unit without admin privileges")
            return {
                "detail": {
                    "message": "Only administrators can add health units",
                    "status_code": 403
                }
            }
        
            
        return await self.health_unit_use_cases.add_health_unit(health_unit, audit_data)

    async def get_health_units(self, request: Request):
        """
        Retrieves health units.
        If the user is an administrator, returns their own units.
        If a professional, returns the units of their administrator.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_health_units",
            "ip_address": request.client.host
        }
        if request.state.user.get("profile") == "general_administrator":
            return await self.health_unit_use_cases.get_health_units(audit_data)
        elif request.state.user.get("profile") == "administrator":
            admin_id = request.state.user.get("user_id")
            return await self.health_unit_use_cases.get_health_units(audit_data, admin_id)
        else:
            logger.warning(f"User {audit_data['user_id']} attempted to get health units without admin privileges")
            return {
                "detail": {
                    "message": "Only administrators can view health units",
                    "status_code": 403
                }
            }
        
    async def get_health_unit_by_id(self, request: Request, unit_id: str):
        """
        Retrieves a health unit by ID.
        Users can only see units associated with their administrator.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_health_unit_by_id",
            "target_unit_id": unit_id,
            "ip_address": request.client.host
        }
        
        return await self.health_unit_use_cases.get_health_unit_by_id(unit_id, audit_data)

    async def update_health_unit(self, request: Request, unit_id: str, health_unit: UpdateHealthUnit):
        """
        Updates information of a health unit.
        Only administrators can update their own units.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "update_health_unit",
            "target_unit_id": unit_id,
            "ip_address": request.client.host
        }
        
        if request.state.user.get("profile") != "administrator" and request.state.user.get("profile") != "general_administrator":
            logger.warning(f"User {audit_data['user_id']} attempted to update health unit without admin privileges")
            return {
                "detail": {
                    "message": "Only administrators can update health units",
                    "status_code": 403
                }
            }
        
        return await self.health_unit_use_cases.update_health_unit(unit_id, health_unit, audit_data)

    async def delete_health_unit(self, request: Request, unit_id: str):
        """
        Removes a health unit.
        Only administrators can remove their own units.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "delete_health_unit",
            "target_unit_id": unit_id,
            "ip_address": request.client.host,
            "profile": request.state.user.get("profile")
        }
        
        if request.state.user.get("profile") != "administrator" and request.state.user.get("profile") != "general_administrator":
            logger.warning(f"User {audit_data['user_id']} attempted to delete health unit without admin privileges")
            return {
                "detail": {
                    "message": "Only administrators can delete health units",
                    "status_code": 403
                }
            }
        
        return await self.health_unit_use_cases.delete_health_unit(unit_id, audit_data)
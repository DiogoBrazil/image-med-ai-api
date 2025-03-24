from fastapi import Request
from ..interfaces.create_health_unit import CreateHealthUnit
from ..interfaces.update_health_unit import UpdateHealthUnit
from ..usecases.health_unit import HealthUnitService
from ..utils.credentials_middleware import AuthMiddleware
from ..utils.logger import get_logger

logger = get_logger(__name__)

class HealthUnitController:
    def __init__(self):
        self.health_unit_service = HealthUnitService()
        self.auth_middleware = AuthMiddleware()
    
    async def add_health_unit(self, request: Request, health_unit: CreateHealthUnit):
        """
        Adiciona uma nova unidade de saúde.
        Requer perfil de administrador.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "add_health_unit",
            "ip_address": request.client.host
        }
        
        # Apenas administradores podem adicionar unidades de saúde
        if request.state.user.get("profile") != "administrator":
            logger.warning(f"User {audit_data['user_id']} attempted to add health unit without admin privileges")
            return {
                "detail": {
                    "message": "Only administrators can add health units",
                    "status_code": 403
                }
            }
        
        # O admin_id da unidade deve ser o ID do administrador logado
        admin_id = request.state.user.get("user_id")
            
        return await self.health_unit_service.add_health_unit(health_unit, admin_id, audit_data)

    async def get_health_units(self, request: Request):
        """
        Recupera unidades de saúde.
        Se o usuário for administrador, retorna suas próprias unidades.
        Se for profissional, retorna as unidades do seu administrador.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_health_units",
            "ip_address": request.client.host
        }
        
        # Determinar o admin_id com base no perfil do usuário
        if request.state.user.get("profile") == "administrator":
            admin_id = request.state.user.get("user_id")
        else:  # profissional
            admin_id = request.state.user.get("admin_id")
            
            if not admin_id:
                logger.warning(f"Professional {audit_data['user_id']} has no admin_id but attempted to get health units")
                return {
                    "detail": {
                        "message": "You don't have permission to access this resource",
                        "status_code": 403
                    }
                }
        
        return await self.health_unit_service.get_health_units(admin_id, audit_data)

    async def get_health_unit_by_id(self, request: Request, unit_id: str):
        """
        Recupera uma unidade de saúde pelo ID.
        Usuários só podem ver unidades associadas ao seu administrador.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_health_unit_by_id",
            "target_unit_id": unit_id,
            "ip_address": request.client.host
        }
        
        # A verificação de permissão será feita no service, que verificará
        # se a unidade pertence ao administrador correto
        
        return await self.health_unit_service.get_health_unit_by_id(unit_id, audit_data)

    async def update_health_unit(self, request: Request, unit_id: str, health_unit: UpdateHealthUnit):
        """
        Atualiza informações de uma unidade de saúde.
        Apenas administradores podem atualizar suas próprias unidades.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "update_health_unit",
            "target_unit_id": unit_id,
            "ip_address": request.client.host
        }
        
        # Apenas administradores podem atualizar unidades de saúde
        if request.state.user.get("profile") != "administrator":
            logger.warning(f"User {audit_data['user_id']} attempted to update health unit without admin privileges")
            return {
                "detail": {
                    "message": "Only administrators can update health units",
                    "status_code": 403
                }
            }
        
        # A verificação se a unidade pertence ao administrador será feita no service
        
        return await self.health_unit_service.update_health_unit(unit_id, health_unit, audit_data)

    async def delete_health_unit(self, request: Request, unit_id: str):
        """
        Remove uma unidade de saúde.
        Apenas administradores podem remover suas próprias unidades.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "delete_health_unit",
            "target_unit_id": unit_id,
            "ip_address": request.client.host
        }
        
        # Apenas administradores podem remover unidades de saúde
        if request.state.user.get("profile") != "administrator":
            logger.warning(f"User {audit_data['user_id']} attempted to delete health unit without admin privileges")
            return {
                "detail": {
                    "message": "Only administrators can delete health units",
                    "status_code": 403
                }
            }
        
        # A verificação se a unidade pertence ao administrador será feita no service
        
        return await self.health_unit_service.delete_health_unit(unit_id, audit_data)
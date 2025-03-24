from fastapi import Request, Query
from typing import Optional
from ..interfaces.create_attendance import CreateAttendance
from ..interfaces.update_attendance import UpdateAttendance
from ..usecases.attendance import AttendanceService
from ..utils.credentials_middleware import AuthMiddleware
from ..utils.logger import get_logger

logger = get_logger(__name__)

class AttendanceController:
    def __init__(self):
        self.attendance_service = AttendanceService()
        self.auth_middleware = AuthMiddleware()
    
    async def add_attendance(self, request: Request, attendance: CreateAttendance):
        """
        Adiciona um novo registro de atendimento com diagnóstico.
        Requer perfil de profissional.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "add_attendance",
            "ip_address": request.client.host
        }
        
        # Apenas profissionais podem adicionar atendimentos
        if request.state.user.get("profile") != "professional":
            logger.warning(f"User {audit_data['user_id']} attempted to add attendance without professional privileges")
            return {
                "detail": {
                    "message": "Only healthcare professionals can add attendances",
                    "status_code": 403
                }
            }
        
        # O professional_id é o ID do usuário logado
        professional_id = request.state.user.get("user_id")
            
        return await self.attendance_service.add_attendance(attendance, professional_id, audit_data)

    async def get_attendances(
        self, 
        request: Request, 
        health_unit_id: Optional[str] = None,
        model_used: Optional[str] = None,
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0)
    ):
        """
        Recupera registros de atendimento com filtros opcionais.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_attendances",
            "ip_address": request.client.host
        }
        
        # Determinar os parâmetros de filtro com base no perfil do usuário
        user_profile = request.state.user.get("profile")
        
        if user_profile == "administrator":
            # Admin vê apenas os atendimentos das suas unidades
            admin_id = request.state.user.get("user_id")
            professional_id = None
        else:  # profissional
            # Profissional vê apenas seus próprios atendimentos
            admin_id = request.state.user.get("admin_id")
            professional_id = request.state.user.get("user_id")
        
        return await self.attendance_service.get_attendances(
            admin_id=admin_id,
            health_unit_id=health_unit_id,
            professional_id=professional_id,
            model_used=model_used,
            limit=limit,
            offset=offset,
            audit_data=audit_data
        )

    async def get_attendance_by_id(self, request: Request, attendance_id: str, include_image: bool = False):
        """
        Recupera um registro de atendimento pelo ID.
        Parâmetro include_image controla se a imagem base64 completa é retornada.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_attendance_by_id",
            "target_attendance_id": attendance_id,
            "ip_address": request.client.host
        }
        
        # A verificação de permissão (se o usuário pode acessar este atendimento)
        # será feita no service, com base no perfil e relacionamentos
        
        return await self.attendance_service.get_attendance_by_id(
            attendance_id, 
            include_image, 
            audit_data
        )

    async def update_attendance(self, request: Request, attendance_id: str, attendance: UpdateAttendance):
        """
        Atualiza informações de um registro de atendimento.
        Profissionais só podem atualizar seus próprios registros.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "update_attendance",
            "target_attendance_id": attendance_id,
            "ip_address": request.client.host
        }
        
        # O ID do usuário atual é passado para verificação de permissão no service
        professional_id = request.state.user.get("user_id")
        
        return await self.attendance_service.update_attendance(
            attendance_id, 
            attendance, 
            professional_id, 
            audit_data
        )

    async def delete_attendance(self, request: Request, attendance_id: str):
        """
        Remove um registro de atendimento.
        Profissionais só podem remover seus próprios registros.
        Administradores podem remover qualquer registro de suas unidades.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "delete_attendance",
            "target_attendance_id": attendance_id,
            "ip_address": request.client.host
        }
        
        # O ID do usuário atual é passado para verificação de permissão no service
        professional_id = request.state.user.get("user_id")
        
        return await self.attendance_service.delete_attendance(
            attendance_id,
            professional_id,
            audit_data
        )
        
    async def get_statistics(
        self,
        request: Request,
        period: str = Query("month", regex="^(day|week|month|year)$")
    ):
        """
        Obtém estatísticas sobre o uso e precisão dos modelos.
        Apenas administradores podem acessar estas estatísticas.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_statistics",
            "period": period,
            "ip_address": request.client.host
        }
        
        # Apenas administradores podem acessar estatísticas
        if request.state.user.get("profile") != "administrator":
            logger.warning(f"User {audit_data['user_id']} attempted to access statistics without admin privileges")
            return {
                "detail": {
                    "message": "Only administrators can access statistics",
                    "status_code": 403
                }
            }
        
        # O admin_id é o ID do administrador logado
        admin_id = request.state.user.get("user_id")
        
        return await self.attendance_service.get_statistics(
            admin_id,
            period,
            audit_data
        )
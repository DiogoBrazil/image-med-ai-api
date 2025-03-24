from fastapi import Request, Depends
from ..interfaces.create_user import CreateUser
from ..interfaces.update_user import UpdateUser
from ..interfaces.login_user import LoginUser
from ..usecases.user import UserService
from ..utils.credentials_middleware import AuthMiddleware
from ..utils.logger import get_logger

logger = get_logger(__name__)

class UserController:
    def __init__(self):
        self.user_service = UserService()
        self.auth_middleware = AuthMiddleware()
    
    async def add_user(self, request: Request, user: CreateUser):
        """
        Adiciona um novo usuário.
        Requer perfil de administrador.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "add_user",
            "ip_address": request.client.host
        }
        
        # Apenas administradores podem adicionar usuários
        if request.state.user.get("profile") != "administrator":
            logger.warning(f"User {audit_data['user_id']} attempted to add user without admin privileges")
            return {
                "detail": {
                    "message": "Only administrators can add users",
                    "status_code": 403
                }
            }
            
        return await self.user_service.add_user(user, audit_data)

    async def login_user(self, request: Request, user: LoginUser):
        """
        Realiza login de usuário.
        Não requer autenticação prévia.
        """
        # Para login, só precisamos verificar a API Key, não o token
        api_key = request.headers.get('api_key')
        self.auth_middleware._verify_api_key(api_key)
        
        # Dados de auditoria baseados no IP
        audit_data = {
            "email": user.email,
            "action": "login",
            "ip_address": request.client.host
        }
        
        return await self.user_service.login_user(user, audit_data)

    async def get_users(self, request: Request, admin_id: str = None):
        """
        Recupera todos os usuários.
        Se admin_id for fornecido, retorna apenas usuários associados a esse admin.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_users",
            "ip_address": request.client.host
        }
        
        # Se o usuário for um profissional, só pode ver outros usuários do mesmo admin
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
        
        return await self.user_service.get_users(admin_id, audit_data)

    async def get_user_by_id(self, request: Request, user_id: str):
        """
        Recupera um usuário pelo ID.
        Usuários só podem ver seus próprios dados ou, se administradores, 
        dados de usuários vinculados a eles.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_user_by_id",
            "target_user_id": user_id,
            "ip_address": request.client.host
        }
        
        # Verificar permissão: usuário só pode ver seus próprios dados ou, 
        # se administrador, dados de usuários vinculados a ele
        current_user_id = request.state.user.get("user_id")
        current_user_profile = request.state.user.get("profile")
        
        if user_id != current_user_id and current_user_profile != "administrator":
            logger.warning(f"User {current_user_id} attempted to access data of another user {user_id}")
            return {
                "detail": {
                    "message": "You don't have permission to access this user's data",
                    "status_code": 403
                }
            }
        
        return await self.user_service.get_user_by_id(user_id, audit_data)

    async def update_user(self, request: Request, user_id: str, user: UpdateUser):
        """
        Atualiza informações de um usuário.
        Usuários só podem atualizar seus próprios dados ou, se administradores,
        dados de usuários vinculados a eles.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "update_user",
            "target_user_id": user_id,
            "ip_address": request.client.host
        }
        
        # Verificar permissão: usuário só pode atualizar seus próprios dados ou,
        # se administrador, dados de usuários vinculados a ele
        current_user_id = request.state.user.get("user_id")
        current_user_profile = request.state.user.get("profile")
        
        if user_id != current_user_id and current_user_profile != "administrator":
            logger.warning(f"User {current_user_id} attempted to update data of another user {user_id}")
            return {
                "detail": {
                    "message": "You don't have permission to update this user's data",
                    "status_code": 403
                }
            }
        
        return await self.user_service.update_user(user_id, user, audit_data)

    async def delete_user(self, request: Request, user_id: str):
        """
        Remove um usuário.
        Apenas administradores podem remover usuários.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "delete_user",
            "target_user_id": user_id,
            "ip_address": request.client.host
        }
        
        # Apenas administradores podem remover usuários
        if request.state.user.get("profile") != "administrator":
            logger.warning(f"User {audit_data['user_id']} attempted to delete user without admin privileges")
            return {
                "detail": {
                    "message": "Only administrators can delete users",
                    "status_code": 403
                }
            }
        
        return await self.user_service.delete_user(user_id, audit_data)
        
    async def get_administrators(self, request: Request):
        """
        Recupera todos os administradores.
        Apenas para uso interno ou super administradores.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_administrators",
            "ip_address": request.client.host
        }
        
        # Verificar se o usuário tem permissão para listar administradores
        # Esta verificação pode variar dependendo dos requisitos específicos
        if request.state.user.get("profile") != "administrator":
            logger.warning(f"User {audit_data['user_id']} attempted to list administrators without admin privileges")
            return {
                "detail": {
                    "message": "You don't have permission to list administrators",
                    "status_code": 403
                }
            }
            
        return await self.user_service.get_administrators(audit_data)
        
    async def get_professionals(self, request: Request, admin_id: str = None):
        """
        Recupera profissionais associados a um administrador.
        Se admin_id não for fornecido, usa o ID do administrador do token.
        """
        await self.auth_middleware.verify_request(request)
        
        # Extrair informações do token para auditoria
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_professionals",
            "ip_address": request.client.host
        }
        
        current_user_profile = request.state.user.get("profile")
        current_user_id = request.state.user.get("user_id")
        
        # Se não for fornecido admin_id e o usuário for admin, usa o ID do usuário atual
        if not admin_id and current_user_profile == "administrator":
            admin_id = current_user_id
        
        # Se for profissional, só pode ver profissionais do mesmo admin
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
        
        return await self.user_service.get_professionals(admin_id, audit_data)
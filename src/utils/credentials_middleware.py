from fastapi import Request, HTTPException
import jwt
from src.config.settings import Settings
from src.adapters.token_adapter import TokenAdapter
from src.utils.logger import get_logger

settings = Settings()
logger = get_logger(__name__)

class AuthMiddleware:
    def __init__(self):
        self.token_adapter = TokenAdapter()
    
    async def verify_request(self, request: Request):
        """
        Verifica credenciais da requisição com base na rota.
        
        Verifica a API key para todas as rotas.
        Para rotas protegidas, verifica também o token JWT.
        Para rotas de admin, verifica se o usuário é administrador.
        """
        # Obter cabeçalhos
        api_key = request.headers.get('api_key')
        token_value = request.headers.get('Authorization')
        
        # Rotas públicas (apenas API key)
        public_paths = [
            '/api/auth/login',
            '/api/health',
            '/api/docs',
            '/api/openapi.json'
        ]
        
        # Verificar API key para todas as requisições
        self._verify_api_key(api_key)
        
        # Se for uma rota pública, não precisa de token
        if any([request.url.path.startswith(path) for path in public_paths]):
            return
        
        # Para outras rotas, verificar token
        token_data = await self._verify_token(token_value)
        
        # Para rotas de admin, verificar permissão
        if self._is_admin_route(request.url.path):
            self._verify_admin_access(token_data)
        
        # Para rotas específicas de profissionais, verificar perfil
        if self._is_professional_route(request.url.path):
            self._verify_professional_access(token_data)
        
        # Verificar permissão de acesso à unidade de saúde
        if self._is_health_unit_route(request.url.path):
            health_unit_id = self._extract_health_unit_id(request.url.path)
            if health_unit_id:
                await self._verify_health_unit_access(token_data, health_unit_id)
        
        # Adicionar dados do token ao request para uso nos endpoints
        request.state.user = token_data
    
    def _verify_api_key(self, api_key: str):
        """Verifica se a API key é válida."""
        if not api_key:
            logger.warning("API Key missing in request")
            raise HTTPException(status_code=400, detail={"message": "API Key is required", "status_code": 400})
        
        if api_key != settings.API_KEY:
            logger.warning("Invalid API Key provided")
            raise HTTPException(status_code=403, detail={"message": "Invalid API Key", "status_code": 403})
    
    async def _verify_token(self, token_value: str):
        """Verifica e decodifica o token JWT."""
        if not token_value:
            logger.warning("Token missing in request")
            raise HTTPException(status_code=401, detail={"message": "Authorization token is required", "status_code": 401})
        
        # Extrair token do cabeçalho (formato: "Bearer <token>")
        try:
            token = token_value.split(' ')[1] if token_value.startswith('Bearer ') else token_value
        except IndexError:
            logger.warning("Invalid Authorization header format")
            raise HTTPException(status_code=401, detail={"message": "Invalid Authorization header format. Use 'Bearer <token>'", "status_code": 401})
        
        # Verificar e decodificar token
        try:
            decoded_token = await self.token_adapter.decode_token(token)
            return decoded_token
        except jwt.ExpiredSignatureError:
            logger.warning("Expired token provided")
            raise HTTPException(status_code=401, detail={"message": "Token has expired", "status_code": 401})
        except jwt.PyJWTError as e:
            logger.warning(f"Invalid token provided: {str(e)}")
            raise HTTPException(status_code=401, detail={"message": f"Invalid token: {str(e)}", "status_code": 401})
    
    def _verify_admin_access(self, token_data: dict):
        """Verifica se o usuário tem perfil de administrador."""
        if token_data.get('profile') != 'administrator':
            logger.warning(f"User {token_data.get('user_id')} tried to access admin route without admin privileges")
            raise HTTPException(status_code=403, detail={
                "message": "Unauthorized. This request can only be made by administrators.",
                "status_code": 403
            })
    
    def _verify_professional_access(self, token_data: dict):
        """Verifica se o usuário tem perfil de profissional."""
        if token_data.get('profile') != 'professional':
            logger.warning(f"User {token_data.get('user_id')} tried to access professional route without appropriate privileges")
            raise HTTPException(status_code=403, detail={
                "message": "Unauthorized. This request can only be made by healthcare professionals.",
                "status_code": 403
            })
    
    async def _verify_health_unit_access(self, token_data: dict, health_unit_id: str):
        """
        Verifica se o usuário tem acesso à unidade de saúde específica.
        Esta implementação depende do repository, então apenas definimos a interface.
        """
        # Esta verificação seria implementada no controller, usando o repository
        # para verificar se a unidade pertence ao admin do usuário
        pass
    
    def _is_admin_route(self, path: str) -> bool:
        """Verifica se a rota é exclusiva para administradores."""
        admin_routes = [
            '/api/admin/',
            '/api/health-units/create',
            '/api/users/professionals/create',
            '/api/statistics/'
        ]
        return any([path.startswith(route) for route in admin_routes])
    
    def _is_professional_route(self, path: str) -> bool:
        """Verifica se a rota é exclusiva para profissionais."""
        professional_routes = [
            '/api/attendances/create',
            '/api/diagnoses/'
        ]
        return any([path.startswith(route) for route in professional_routes])
    
    def _is_health_unit_route(self, path: str) -> bool:
        """Verifica se a rota envolve acesso a uma unidade de saúde específica."""
        return '/api/health-units/' in path and not path.endswith('/health-units/')
    
    def _extract_health_unit_id(self, path: str) -> str:
        """Extrai o ID da unidade de saúde da URL, se presente."""
        parts = path.split('/')
        for i, part in enumerate(parts):
            if part == 'health-units' and i + 1 < len(parts):
                return parts[i + 1]
        return None
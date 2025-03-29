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
        Verifies request credentials based on the route.
        
        Checks API key for all routes.
        For protected routes, also checks JWT token.
        For admin routes, verifies if the user is an administrator.
        """
        api_key = request.headers.get('api_key')
        token_value = request.headers.get('Authorization')
        
        public_paths = [
            '/api/auth/login',
            '/api/status',
            '/api/docs',
            '/api/openapi.json'
        ]
        

        await self._verify_api_key(api_key)
        
        
        if any([request.url.path.startswith(path) for path in public_paths]):
            return
        

        token_data = await self._verify_token(token_value)


        if request.url.path == '/api/users/subscriptions' or request.url.path.startswith('/api/users/subscriptions/'):

            if token_data.get('profile') != 'general_administrator':
                raise HTTPException(status_code=403, detail={
                    "message": "Only general administrators can access subscriptions",
                    "status_code": 403
                })

        elif await self._is_admin_route(request.url.path):
            await self._verify_admin_access(token_data)
        

        if await self._is_professional_route(request.url.path):
            await self._verify_professional_access(token_data)
        

        if await self._is_health_unit_route(request.url.path):
            health_unit_id = await self._extract_health_unit_id(request.url.path)
            if health_unit_id:
                await self._verify_health_unit_access(token_data, health_unit_id)
        

        request.state.user = token_data
    
    async def _verify_api_key(self, api_key: str):
        """Checks if the API key is valid."""
        if not api_key:
            logger.warning("API Key missing in request")
            raise HTTPException(status_code=400, detail={"message": "API Key is required", "status_code": 400})
        
        if api_key != settings.API_KEY:
            logger.warning("Invalid API Key provided")
            raise HTTPException(status_code=403, detail={"message": "Invalid API Key", "status_code": 403})
    
    async def _verify_token(self, token_value: str):
        """Verifies and decodes the JWT token."""
        if not token_value:
            logger.warning("Token missing in request")
            raise HTTPException(status_code=401, detail={"message": "Authorization token is required", "status_code": 401})
        

        try:
            token = token_value.split(' ')[1] if token_value.startswith('Bearer ') else token_value
        except IndexError:
            logger.warning("Invalid Authorization header format")
            raise HTTPException(status_code=401, detail={"message": "Invalid Authorization header format. Use 'Bearer <token>'", "status_code": 401})
        

        try:
            decoded_token = await self.token_adapter.decode_token(token)
            return decoded_token
        except jwt.ExpiredSignatureError:
            logger.warning("Expired token provided")
            raise HTTPException(status_code=401, detail={"message": "Token has expired", "status_code": 401})
        except jwt.PyJWTError as e:
            logger.warning(f"Invalid token provided: {str(e)}")
            raise HTTPException(status_code=401, detail={"message": f"Invalid token: {str(e)}", "status_code": 401})
    
    async def _verify_admin_access(self, token_data: dict):
        """Checks if the user has an administrator profile."""
        if token_data.get('profile') != 'general_administrator':
            logger.warning(f"User {token_data.get('user_id')} tried to access admin route without admin privileges")
            raise HTTPException(status_code=403, detail={
                "message": "Unauthorized. This request can only be made by administrators.",
                "status_code": 403
            })
    
    async def _verify_professional_access(self, token_data: dict):
        """Checks if the user has a professional profile."""
        if token_data.get('profile') != 'professional':
            logger.warning(f"User {token_data.get('user_id')} tried to access professional route without appropriate privileges")
            raise HTTPException(status_code=403, detail={
                "message": "Unauthorized. This request can only be made by healthcare professionals.",
                "status_code": 403
            })
    
    async def _verify_health_unit_access(self, token_data: dict, health_unit_id: str):
        """
        Checks if the user has access to the specific health unit.
        This implementation depends on the repository, so we only define the interface.
        """


        pass
    
    async def _is_admin_route(self, path: str) -> bool:
        """Checks if the route is exclusive for administrators."""
        admin_routes = [
            '/api/admin/',
            '/api/health-units/create',
            '/api/users/professionals/create',
            '/api/statistics/',
            '/api/users/subscriptions'
        ]
        return any([path.startswith(route) for route in admin_routes])
    
    async def _is_professional_route(self, path: str) -> bool:
        """Checks if the route is exclusive for professionals."""
        professional_routes = [
            '/api/attendances/create',
            '/api/diagnoses/'
        ]
        return any([path.startswith(route) for route in professional_routes])
    
    async def _is_health_unit_route(self, path: str) -> bool:
        """Checks if the route involves access to a specific health unit."""
        return '/api/health-units/' in path and not path.endswith('/health-units/')
    
    async def _extract_health_unit_id(self, path: str) -> str:
        """Extracts the health unit ID from the URL, if present."""
        parts = path.split('/')
        for i, part in enumerate(parts):
            if part == 'health-units' and i + 1 < len(parts):
                return parts[i + 1]
        return None
import jwt
import datetime
from src.config.settings import Settings

settings = Settings()


class TokenAdapter:
    def __init__(self, token_expiration_minutes=1440):
        self.secret_key = settings.SECRET_KEY
        self.token_expiration_minutes = token_expiration_minutes

    async def create_token(self, user_id, full_name, email, profile, admin_id=None):
        """
        Create a JWT token for a user.
        
        Args:
            user_id: The user's UUID
            name: The user's full name
            email: The user's email address
            profile: The user's profile (general_administrator, administrator or professional)
            admin_id: If the user is a professional, the admin they're associated with
            
        Returns:
            str: Encoded JWT token
        """
        expiration_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=self.token_expiration_minutes)
        
        payload = {
            "user_id": str(user_id),
            "full_name": full_name,
            "email": email,
            "profile": profile,
            "exp": expiration_time
        }
        
        if profile == "professional" and admin_id:
            payload["admin_id"] = str(admin_id)
            
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    async def create_token_for_admin(self, user_id, full_name, email):
        """
        Create a simplified token specifically for administrators.
        
        Args:
            user_id: The admin's UUID
            name: The admin's full name
            email: The admin's email address
            
        Returns:
            str: Encoded JWT token
        """
        expiration_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=self.token_expiration_minutes)
        
        payload = {
            "user_id": str(user_id),
            "full_name": full_name,
            "email": email,
            "profile": "administrator",
            "exp": expiration_time
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    async def decode_token(self, token):
        """
        Decode and validate a JWT token.
        
        Args:
            token: The JWT token to decode
            
        Returns:
            dict: The decoded token payload
            
        Raises:
            jwt.PyJWTError: If the token is invalid or expired
        """
        try:
            return jwt.decode(token, self.secret_key, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:

            raise jwt.PyJWTError("Token has expired")
        except jwt.PyJWTError as e:

            raise jwt.PyJWTError(f"Invalid token: {str(e)}")
            
    async def get_user_id_from_token(self, token):
        """
        Extract just the user_id from a token.
        
        Args:
            token: The JWT token
            
        Returns:
            str: The user's UUID
            
        Raises:
            jwt.PyJWTError: If the token is invalid or expired
        """
        decoded = await self.decode_token(token)
        return decoded.get("user_id")
        
    async def get_admin_id_from_token(self, token):
        """
        Extract the admin_id from a token if present.
        For professional users, returns their associated admin's ID.
        For admin users, returns their own ID.
        
        Args:
            token: The JWT token
            
        Returns:
            str: The admin UUID or None if not applicable
            
        Raises:
            jwt.PyJWTError: If the token is invalid or expired
        """
        decoded = await self.decode_token(token)
        profile = decoded.get("profile")
        
        if profile == "administrator" and profile == "general_administrator":
            return decoded.get("user_id")
        elif profile == "professional":
            return decoded.get("admin_id")
        return None
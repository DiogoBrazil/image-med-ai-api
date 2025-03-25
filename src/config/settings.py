from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):

    POSTGRES_URL: str
    

    SECRET_KEY: str
    API_KEY: str
    

    USER_NAME_ROOT: str
    USER_EMAIL_ROOT: str
    USER_ROOT_PASSWORD: str
    USER_ROOT_PROFILE: str
    USER_STATUS_ROOT: str = "active"
    

    def get_database(self) -> str:
        """Retorna a string de conexão com o banco de dados PostgreSQL."""
        return self.POSTGRES_URL

    class Config:
        env_file = ".env"
        case_sensitive = True
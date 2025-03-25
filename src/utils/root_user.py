from src.repositories.user_repository import UserRepository
from src.adapters.password_adapter import PasswordAdapter
from src.config.settings import Settings
from src.utils.logger import get_logger
import asyncpg
from fastapi import HTTPException
from ..utils.error_handler import raise_http_error

async def ensure_root_user():
    """
    Verifica se o usuário administrador raiz existe.
    Se não existir, cria-o com os dados definidos nas variáveis de ambiente.
    
    Returns:
        dict: Status da operação com mensagem de resultado
    
    Raises:
        HTTPException: Em caso de erros críticos que impedem o início da aplicação
    """
    
    logger = get_logger("root_user_setup")
    settings = Settings()
    user_repo = UserRepository()
    password_adapter = PasswordAdapter()
    
    try:

        logger.info("Testando conexão com o banco de dados...")
        try:

            db_url = settings.POSTGRES_URL
            db_info = db_url.split("@")[-1] if "@" in db_url else db_url
            logger.info(f"Tentando conectar a: {db_info}")
            

            conn = await asyncpg.connect(settings.POSTGRES_URL)
            await conn.close()
            logger.info("Conexão com banco de dados estabelecida com sucesso")
        except Exception as conn_err:
            error_msg = f"Erro ao conectar ao banco de dados: {str(conn_err)}"
            logger.error(error_msg)
            logger.error(f"Verifique se a URL do banco de dados está correta: {settings.POSTGRES_URL}")
            raise_http_error(500, error_msg)
        

        try:
            await user_repo.init_pool()
        except Exception as pool_err:
            error_msg = f"Erro ao inicializar pool de conexões: {str(pool_err)}"
            logger.error(error_msg)
            raise_http_error(500, error_msg)
        

        try:
            existing_user = await user_repo.get_user_by_email(settings.USER_EMAIL_ROOT)
            
            if existing_user:
                logger.info(f"Usuário administrador raiz já existe: {settings.USER_EMAIL_ROOT}")
                return {
                    "status": "Error",
                    "message": f"Usuário administrador raiz já existe",
                    "status_code": 403
                }
        except Exception as user_check_err:
            error_msg = f"Erro ao verificar usuário existente: {str(user_check_err)}"
            logger.error(error_msg)
            raise_http_error(500, error_msg)
        

        valid_profiles = ["general_administrator", "administrator", "professional"]
        if settings.USER_ROOT_PROFILE not in valid_profiles:
            error_msg = f"Perfil inválido: {settings.USER_ROOT_PROFILE}. Perfis válidos: {', '.join(valid_profiles)}"
            logger.error(error_msg)
            raise_http_error(400, error_msg)
        

        logger.info(f"Criando usuário administrador raiz: {settings.USER_EMAIL_ROOT}")
        
        try:

            hashed_password = await password_adapter.hash_password(settings.USER_ROOT_PASSWORD)
            

            user_data = {
                "full_name": settings.USER_NAME_ROOT,
                "email": settings.USER_EMAIL_ROOT,
                "password_hash": hashed_password,
                "profile": settings.USER_ROOT_PROFILE,
                "admin_id": None,
                "status": settings.USER_STATUS_ROOT
            }
            

            result = await user_repo.add_user(user_data)
            
            if result["added"]:
                success_msg = f"Usuário administrador raiz criado com sucesso: {result['user_id']}"
                logger.info(success_msg)
                return {
                    "status": "success",
                    "message": success_msg,
                    "user_id": result["user_id"]
                }
            else:
                error_msg = "Falha ao criar usuário administrador raiz"
                logger.error(error_msg)
                raise_http_error(500, error_msg)
        except HTTPException as http_exc:

            raise http_exc
        except Exception as user_create_err:
            error_msg = f"Erro ao criar usuário raiz: {str(user_create_err)}"
            logger.error(error_msg)
            raise_http_error(500, error_msg)
    
    except HTTPException:

        raise
    except Exception as e:

        error_msg = f"Erro inesperado ao verificar/criar usuário administrador raiz: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        raise_http_error(500, error_msg)
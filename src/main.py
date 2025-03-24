from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import uuid
from .routes.user_routes import router as user_router
from .routes.health_unit_routes import router as health_unit_router
from .routes.attendance_routes import router as attendance_router
from .utils.custom_openapi import custom_openapi
from .config.settings import Settings
from .utils.logger import get_logger
from .utils.root_user import ensure_root_user


# Carregar variáveis de ambiente
load_dotenv()

# Carregar configurações
settings = Settings()
logger = get_logger("api")

# Criar aplicação FastAPI
app = FastAPI(
    title="Medical Diagnosis By Images API",
    description="API para sistema de diagnóstico médico por IA usando imagens de raio-x e mamografias.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

# Configurar esquema OpenAPI personalizado
app.openapi = lambda: custom_openapi(app)

# Middleware para logging de requisições
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Log de início da requisição
    logger.info(f"Request {request_id} started: {request.method} {request.url.path}")
    
    # Processar a requisição
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log de conclusão da requisição
        logger.info(f"Request {request_id} completed: {response.status_code} in {process_time:.3f}s")
        
        # Adicionar headers de tempo de processamento
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request {request_id} failed after {process_time:.3f}s: {str(e)}")
        
        # Retornar erro 500 em caso de exceção não tratada
        return JSONResponse(
            status_code=500,
            content={"detail": {"message": "Internal server error", "status_code": 500}}
        )

# Rota de verificação de saúde da API
@app.get("/api/health", tags=["health"])
async def health_check():
    """
    Verifica se a API está funcionando corretamente.
    """
    return {"status": "healthy", "version": "1.0.0"}

# ROta para criar admin_root caso não exista
@app.post("/api/ensure-root", tags=["health"])
async def ensure_root():
    """
    Verifica e garante que existe um usuário administrador raiz no sistema.
    Se não existir, cria-o com os dados definidos nas variáveis de ambiente.
    """
    try:
        result = await ensure_root_user()
        # Se ensure_root_user não retornar nada (usuário já existe), crie uma resposta padrão
        if not result:
            return {
                "status": "success",
                "message": "Verificação de usuário administrador concluída",
                "details": "Nenhuma ação foi necessária"
            }
        # Caso contrário, retorne o resultado da função
        return result
    except Exception as e:
        # Capture o erro e retorne uma resposta formatada
        error_message = str(e)
        logger.error(f"Erro ao configurar usuário raiz: {error_message}")
        
        # Extraia código de status se for uma HTTPException
        status_code = 500
        if hasattr(e, 'status_code'):
            status_code = e.status_code
        
        # Retorne a resposta de erro formatada
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "error",
                "message": "Falha ao verificar/criar usuário administrador",
                "details": error_message
            }
        )

# Incluir rotas
app.include_router(user_router)
app.include_router(health_unit_router)
app.include_router(attendance_router)

# Rota raiz
@app.get("/", include_in_schema=False)
async def root():
    """
    Redireciona para a documentação da API.
    """
    return {"message": "Medical Diagnosis API", "docs": "/api/docs"}

# Gerenciador de ciclo de vida usando contexto assíncrono
# @app.lifespan
# async def lifespan(app: FastAPI):
#     logger.info("API iniciando...")
#     try:
#         await ensure_root_user()
#     except Exception as e:
#         logger.error(f"Erro ao configurar usuário raiz: {str(e)}")
#         # Não interrompe a inicialização da aplicação
    
#     # Libera o controle para o FastAPI executar a aplicação
#     yield
    
#     # Código de encerramento
#     logger.info("API encerrando...")

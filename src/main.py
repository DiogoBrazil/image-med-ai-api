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


load_dotenv()

settings = Settings()
logger = get_logger("api")

app = FastAPI(
    title="Medical Diagnosis By Images API",
    description="API for medical diagnostic system using AI with x-ray and mammography images.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.openapi = lambda: custom_openapi(app)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(f"Request {request_id} started: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        logger.info(f"Request {request_id} completed: {response.status_code} in {process_time:.3f}s")
        
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request {request_id} failed after {process_time:.3f}s: {str(e)}")
        
        return JSONResponse(
            status_code=500,
            content={"detail": {"message": "Internal server error", "status_code": 500}}
        )

@app.get("/api/health", tags=["health"])
async def health_check():
    """
    Checks if the API is working correctly.
    """
    return {"status": "healthy", "version": "1.0.0"}

@app.post("/api/ensure-root", tags=["health"])
async def ensure_root():
    """
    Verifies and ensures that a root administrator user exists in the system.
    If it doesn't exist, creates it with data defined in environment variables.
    """
    try:
        result = await ensure_root_user()
        if not result:
            return {
                "status": "success",
                "message": "Administrator user verification completed",
                "details": "No action was needed"
            }
        return result
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error configuring root user: {error_message}")
        
        status_code = 500
        if hasattr(e, 'status_code'):
            status_code = e.status_code
        
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "error",
                "message": "Failed to verify/create administrator user",
                "details": error_message
            }
        )

app.include_router(user_router)
app.include_router(health_unit_router)
app.include_router(attendance_router)

@app.get("/", include_in_schema=False)
async def root():
    """
    Redirects to the API documentation.
    """
    return {"message": "Medical Diagnosis API", "docs": "/api/docs"}
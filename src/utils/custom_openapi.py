from fastapi.openapi.utils import get_openapi
from fastapi import FastAPI

def custom_openapi(app: FastAPI):
    """
    Customizes the OpenAPI schema of the application.
    Adds security schemes for API key and JWT token.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Medical Diagnosis API",
        version="1.0.0",
        description=(
            "API developed for the medical diagnosis system assisted by artificial intelligence. "
            "Provides functionality for user management, health units, and attendance records "
            "with diagnoses using AI models for respiratory diseases, tuberculosis, osteoporosis, and breast cancer. "
            "All endpoints require API key authentication and most also require JWT token authentication."
        ),
        routes=app.routes,
    )


    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}


    openapi_schema["components"]["securitySchemes"]["api_key"] = {
        "type": "apiKey",
        "name": "api_key",
        "in": "header",
        "description": "API key to access the API. Required for all requests."
    }


    openapi_schema["components"]["securitySchemes"]["bearer_token"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT token obtained through the login endpoint. Required for most endpoints."
    }


    openapi_schema["security"] = [
        {"api_key": []},
        {"bearer_token": []}
    ]


    openapi_schema["tags"] = [
        {
            "name": "users",
            "description": "Operações relacionadas a usuários, incluindo administradores e profissionais de saúde.",
        },
        {
            "name": "health-units",
            "description": "Operações relacionadas a unidades de saúde gerenciadas pelos administradores.",
        },
        {
            "name": "attendances",
            "description": "Operações relacionadas a atendimentos e diagnósticos usando modelos de IA.",
        },
        {
            "name": "health",
            "description": "Endpoints para verificação de saúde e diagnóstico da API.",
        }
    ]



    if "paths" in openapi_schema:
        if "/api/users/login" in openapi_schema["paths"]:
            login_path = openapi_schema["paths"]["/api/users/login"]["post"]
            if "requestBody" in login_path:
                login_path["requestBody"]["content"]["application/json"]["example"] = {
                    "email": "admin@example.com",
                    "password": "your_password"
                }


    app.openapi_schema = openapi_schema
    return app.openapi_schema
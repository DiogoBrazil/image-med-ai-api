from fastapi.openapi.utils import get_openapi
from fastapi import FastAPI

def custom_openapi(app: FastAPI):
    """
    Personaliza o esquema OpenAPI da aplicação.
    Adiciona esquemas de segurança para API key e token JWT.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Medical Diagnosis API",
        version="1.0.0",
        description=(
            "API desenvolvida para o sistema de diagnóstico médico assistido por inteligência artificial. "
            "Fornece funcionalidades para gerenciamento de usuários, unidades de saúde e registros de atendimentos "
            "com diagnósticos usando modelos de IA para doenças respiratórias, tuberculose, osteoporose e câncer de mama. "
            "Todos os endpoints requerem autenticação via API key e a maioria também requer autenticação via token JWT."
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
        "description": "API key para acessar a API. Requerida para todas as requisições."
    }


    openapi_schema["components"]["securitySchemes"]["bearer_token"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Token JWT obtido através do endpoint de login. Requerido para a maioria dos endpoints."
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
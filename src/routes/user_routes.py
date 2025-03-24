from fastapi import APIRouter, Request, Depends, Query
from typing import Optional
from ..controllers.user_controller import UserController
from ..interfaces.create_user import CreateUser
from ..interfaces.update_user import UpdateUser
from ..interfaces.login_user import LoginUser

# Definir prefixo para as rotas de usuário
router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

# Instanciar o controller
user_controller = UserController()

@router.post("/", status_code=201, summary="Criar um novo usuário")
async def create_user(request: Request, user: CreateUser):
    """
    Cria um novo usuário no sistema.
    
    - **Requer perfil de administrador**
    - O administrador só pode criar usuários associados a ele
    
    Retorna os detalhes do usuário criado.
    """
    return await user_controller.add_user(request, user)

@router.post("/login", summary="Realizar login de usuário")
async def login(request: Request, user: LoginUser):
    """
    Autentica um usuário e retorna um token JWT.
    
    - **Não requer autenticação prévia**
    - Apenas requer API key válida
    
    Retorna token JWT e informações básicas do usuário.
    """
    return await user_controller.login_user(request, user)

@router.get("/", summary="Listar usuários")
async def get_users(request: Request, admin_id: Optional[str] = None):
    """
    Lista usuários no sistema.
    
    - **Administradores**: Podem ver os usuários vinculados a eles
    - **Profissionais**: Podem ver usuários com o mesmo admin_id
    
    Parâmetros opcionais:
    - **admin_id**: Filtrar por administrador específico
    
    Retorna lista de usuários.
    """
    return await user_controller.get_users(request, admin_id)

@router.get("/{user_id}", summary="Obter usuário por ID")
async def get_user(request: Request, user_id: str):
    """
    Recupera informações de um usuário específico.
    
    - **Usuários**: Podem ver apenas seus próprios dados
    - **Administradores**: Podem ver dados de usuários vinculados a eles
    
    Retorna detalhes do usuário solicitado.
    """
    return await user_controller.get_user_by_id(request, user_id)

@router.put("/{user_id}", summary="Atualizar usuário")
async def update_user(request: Request, user_id: str, user: UpdateUser):
    """
    Atualiza informações de um usuário existente.
    
    - **Usuários**: Podem atualizar apenas seus próprios dados
    - **Administradores**: Podem atualizar dados de usuários vinculados a eles
    
    Retorna confirmação da atualização.
    """
    return await user_controller.update_user(request, user_id, user)

@router.delete("/{user_id}", summary="Remover usuário")
async def delete_user(request: Request, user_id: str):
    """
    Remove um usuário do sistema.
    
    - **Requer perfil de administrador**
    - O administrador só pode remover usuários vinculados a ele
    
    Retorna confirmação da remoção.
    """
    return await user_controller.delete_user(request, user_id)

@router.get("/administrators/list", summary="Listar administradores")
async def get_administrators(request: Request):
    """
    Lista todos os usuários com perfil de administrador.
    
    - **Requer perfil de administrador**
    
    Retorna lista de administradores.
    """
    return await user_controller.get_administrators(request)

@router.get("/professionals/list", summary="Listar profissionais")
async def get_professionals(request: Request, admin_id: Optional[str] = None):
    """
    Lista profissionais de saúde.
    
    - **Administradores**: Podem ver profissionais vinculados a eles
    - **Profissionais**: Podem ver profissionais com o mesmo admin_id
    
    Parâmetros opcionais:
    - **admin_id**: ID do administrador (se não fornecido, usa o ID do administrador atual)
    
    Retorna lista de profissionais.
    """
    return await user_controller.get_professionals(request, admin_id)
from fastapi import APIRouter, Request, Depends, Query
from typing import Optional
from ..controllers.health_unit_controller import HealthUnitController
from ..interfaces.create_health_unit import CreateHealthUnit
from ..interfaces.update_health_unit import UpdateHealthUnit


router = APIRouter(
    prefix="/api/health-units",
    tags=["health-units"],
    responses={404: {"description": "Not found"}},
)


health_unit_controller = HealthUnitController()

@router.post("/", status_code=201, summary="Criar uma nova unidade de saúde")
async def create_health_unit(request: Request, health_unit: CreateHealthUnit):
    """
    Cria uma nova unidade de saúde no sistema.
    
    - **Requer perfil de administrador**
    - A unidade será vinculada automaticamente ao administrador que a criar
    
    Retorna os detalhes da unidade criada.
    """
    return await health_unit_controller.add_health_unit(request, health_unit)

@router.get("/", summary="Listar unidades de saúde")
async def get_health_units(request: Request):
    """
    Lista unidades de saúde no sistema.
    
    - **Administradores**: Podem ver suas próprias unidades
    - **Profissionais**: Podem ver unidades do seu administrador
    
    Retorna lista de unidades de saúde.
    """
    return await health_unit_controller.get_health_units(request)

@router.get("/{unit_id}", summary="Obter unidade de saúde por ID")
async def get_health_unit(request: Request, unit_id: str):
    """
    Recupera informações de uma unidade de saúde específica.
    
    - **Administradores**: Podem ver apenas suas próprias unidades
    - **Profissionais**: Podem ver unidades do seu administrador
    
    Retorna detalhes da unidade solicitada.
    """
    return await health_unit_controller.get_health_unit_by_id(request, unit_id)

@router.put("/{unit_id}", summary="Atualizar unidade de saúde")
async def update_health_unit(request: Request, unit_id: str, health_unit: UpdateHealthUnit):
    """
    Atualiza informações de uma unidade de saúde existente.
    
    - **Requer perfil de administrador**
    - O administrador só pode atualizar suas próprias unidades
    
    Retorna confirmação da atualização.
    """
    return await health_unit_controller.update_health_unit(request, unit_id, health_unit)

@router.delete("/{unit_id}", summary="Remover unidade de saúde")
async def delete_health_unit(request: Request, unit_id: str):
    """
    Remove uma unidade de saúde do sistema.
    
    - **Requer perfil de administrador**
    - O administrador só pode remover suas próprias unidades
    - A unidade não pode ter atendimentos ou profissionais vinculados
    
    Retorna confirmação da remoção.
    """
    return await health_unit_controller.delete_health_unit(request, unit_id)
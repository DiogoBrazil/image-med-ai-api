from typing import Optional
from fastapi import APIRouter, Request
from ..controllers.health_unit_controller import HealthUnitController
from ..interfaces.create_health_unit import CreateHealthUnit
from ..interfaces.update_health_unit import UpdateHealthUnit


router = APIRouter(
    prefix="/api/health-units",
    tags=["health-units"],
    responses={404: {"description": "Not found"}},
)


health_unit_controller = HealthUnitController()

@router.post("/", status_code=201, summary="Create a new health unit")
async def create_health_unit(request: Request, health_unit: CreateHealthUnit):
    """
    Creates a new health unit in the system.
    
    - **Requires administrator profile**
    - The unit will be automatically linked to the administrator who creates it
    
    Returns the details of the created unit.
    """
    return await health_unit_controller.add_health_unit(request, health_unit)

@router.get("/", summary="List health units")
async def get_health_units(request: Request):
    """
    Lists health units in the system.
    
    - **Administrators**: Can see their own units
    - **Professionals**: Can see units of their administrator
    
    Returns list of health units.
    """
    return await health_unit_controller.get_health_units(request)

@router.get("/{unit_id}", summary="Get health unit by ID")
async def get_health_unit(request: Request, unit_id: str):
    """
    Retrieves information of a specific health unit.
    
    - **Administrators**: Can see only their own units
    - **Professionals**: Can see units of their administrator
    
    Returns details of the requested unit.
    """
    return await health_unit_controller.get_health_unit_by_id(request, unit_id)

@router.put("/{unit_id}", summary="Update health unit")
async def update_health_unit(request: Request, unit_id: str, health_unit: UpdateHealthUnit):
    """
    Updates information of an existing health unit.
    
    - **Requires administrator profile**
    - The administrator can only update their own units
    
    Returns confirmation of the update.
    """
    return await health_unit_controller.update_health_unit(request, unit_id, health_unit)

@router.delete("/{unit_id}", summary="Remove health unit")
async def delete_health_unit(request: Request, unit_id: str):
    """
    Removes a health unit from the system.
    
    - **Requires administrator profile**
    - The administrator can only remove their own units
    - The unit cannot have attendances or professionals linked to it
    
    Returns confirmation of the removal.
    """
    return await health_unit_controller.delete_health_unit(request, unit_id)
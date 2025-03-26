from fastapi import APIRouter, Request, Query
from typing import Optional
from ..controllers.attendace_controller import AttendanceController
from ..interfaces.create_attendance import CreateAttendance
from ..interfaces.update_attendance import UpdateAttendance


router = APIRouter(
    prefix="/api/attendances",
    tags=["attendances"],
    responses={404: {"description": "Not found"}},
)


attendance_controller = AttendanceController()

@router.post("/", status_code=201, summary="Create a new attendance")
async def create_attendance(request: Request, attendance: CreateAttendance):
    """
    Registers a new attendance with AI diagnosis.
    
    - **Requires professional profile**
    - Automatically registers the current professional as responsible
    
    Returns the details of the created attendance.
    """
    return await attendance_controller.add_attendance(request, attendance)

@router.get("/", summary="List attendances")
async def get_attendances(
    request: Request, 
    health_unit_id: Optional[str] = None,
    model_used: Optional[str] = Query(None, description="Model type used: respiratory, tuberculosis, osteoporosis, breast"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip")
):
    """
    Lists attendances with optional filters.
    
    - **Administrators**: See attendances from their units
    - **Professionals**: See only their own attendances
    
    Filter parameters:
    - **health_unit_id**: Filter by specific health unit
    - **model_used**: Filter by model type (respiratory, tuberculosis, osteoporosis, breast)
    - **limit**: Maximum number of records (default: 100)
    - **offset**: Pagination (default: 0)
    
    Returns list of attendances.
    """
    return await attendance_controller.get_attendances(
        request, 
        health_unit_id, 
        model_used,
        limit,
        offset
    )

@router.get("/{attendance_id}", summary="Get attendance by ID")
async def get_attendance(
    request: Request, 
    attendance_id: str,
    include_image: bool = Query(False, description="Include full base64 image in the result")
):
    """
    Retrieves information of a specific attendance.
    
    - **Administrators**: Can see attendances from their units
    - **Professionals**: Can see only their own attendances
    
    Parameters:
    - **include_image**: If true, includes the complete base64 image in the response
    
    Returns details of the requested attendance.
    """
    return await attendance_controller.get_attendance_by_id(request, attendance_id, include_image)

@router.put("/{attendance_id}", summary="Update attendance")
async def update_attendance(request: Request, attendance_id: str, attendance: UpdateAttendance):
    """
    Updates information of an existing attendance.
    
    - **Administrators**: Can update attendances from their units
    - **Professionals**: Can update only their own attendances
    
    Returns confirmation of the update.
    """
    return await attendance_controller.update_attendance(request, attendance_id, attendance)

@router.delete("/{attendance_id}", summary="Remove attendance")
async def delete_attendance(request: Request, attendance_id: str):
    """
    Removes an attendance from the system.
    
    - **Administrators**: Can remove attendances from their units
    - **Professionals**: Can remove only their own attendances
    
    Returns confirmation of the removal.
    """
    return await attendance_controller.delete_attendance(request, attendance_id)

@router.get("/statistics/summary", summary="Get attendance statistics")
async def get_statistics(
    request: Request,
    period: str = Query("month", regex="^(day|week|month|year)$", description="Analysis period: day, week, month, year")
):
    """
    Gets statistics on usage and accuracy of AI models.
    
    - **Requires administrator profile**
    - Provides statistics only for the administrator's units
    
    Parameters:
    - **period**: Period for analysis (day, week, month, year)
    
    Returns statistics on usage and accuracy of models.
    """
    return await attendance_controller.get_statistics(request, period)
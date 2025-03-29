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
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page")
):
    """
    Lists attendances with optional filters.
    
    - **General Administrators**: See all attendances system-wide
    - **Administrators**: See attendances from their own units only (with health_unit_id required if admin has multiple units)
    - **Professionals**: Not allowed to access this endpoint
    
    Filter parameters:
    - **health_unit_id**: Filter by specific health unit (required for administrators with multiple health units)
    - **model_used**: Filter by model type (respiratory, tuberculosis, osteoporosis, breast)
    - **page**: Page number (default: 1)
    - **per_page**: Items per page (default: 10, max: 100)
    
    Returns paginated list of attendances with total count and total pages for frontend pagination controls.
    """
    return await attendance_controller.get_attendances(
        request, 
        health_unit_id, 
        model_used,
        page,
        per_page
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
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format")
):
    """
    Gets statistics on usage and accuracy of AI models for a specific date range.
    
    - **General Administrators**: Receive statistics for all attendances across the system
    - **Administrators**: Receive statistics only for their own units
    - **Professionals**: Cannot access this endpoint
    
    Parameters:
    - **start_date**: Start date in YYYY-MM-DD format
    - **end_date**: End date in YYYY-MM-DD format
    
    Returns statistics on model usage count and accuracy percentage within the specified date range.
    """
    return await attendance_controller.get_statistics(request, start_date, end_date)
from fastapi import Request, Query
from typing import Optional
from ..interfaces.create_attendance import CreateAttendance
from ..interfaces.update_attendance import UpdateAttendance
from ..usecases.attendance_usecases import AttendanceUseCases
from ..utils.credentials_middleware import AuthMiddleware
from ..utils.logger import get_logger

logger = get_logger(__name__)

class AttendanceController:
    def __init__(self):
        self.attendance_use_cases = AttendanceUseCases()
        self.auth_middleware = AuthMiddleware()
    
    async def add_attendance(self, request: Request, attendance: CreateAttendance):
        """
        Adds a new attendance record with diagnosis.
        Requires professional profile.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "add_attendance",
            "ip_address": request.client.host
        }
        if request.state.user.get("profile") != "professional":
            logger.warning(f"User {audit_data['user_id']} attempted to add attendance without professional privileges")
            return {
                "detail": {
                    "message": "Only healthcare professionals can add attendances",
                    "status_code": 403
                }
            }
        
        professional_id = request.state.user.get("user_id")
            
        return await self.attendance_use_cases.add_attendance(attendance, professional_id, audit_data)

    async def get_attendances(
        self, 
        request: Request, 
        health_unit_id: Optional[str] = None,
        model_used: Optional[str] = None,
        page: int = 1,
        per_page: int = 10
    ):
        """
        Retrieves attendance records with optional filters.
        Only general_administrator and administrator profiles can access this endpoint.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_attendances",
            "ip_address": request.client.host
        }

        user_profile = request.state.user.get("profile")
        

        if user_profile not in ["general_administrator", "administrator"]:
            logger.warning(f"User {audit_data['user_id']} with profile {user_profile} attempted to access attendances")
            return {
                "detail": {
                    "message": "Only administrators can view attendance lists",
                    "status_code": 403
                }
            }
        

        if user_profile == "general_administrator":
            admin_id = None  # No filter by admin_id means all records
            professional_id = None
        elif user_profile == "administrator":
            admin_id = request.state.user.get("user_id")
            professional_id = None
        else:

            admin_id = request.state.user.get("admin_id")
            professional_id = request.state.user.get("user_id")
        

        offset = (page - 1) * per_page
        
        return await self.attendance_use_cases.get_attendances(
            admin_id=admin_id,
            health_unit_id=health_unit_id,
            professional_id=professional_id,
            model_used=model_used,
            limit=per_page,
            offset=offset,
            page=page,
            per_page=per_page,
            audit_data=audit_data
        )

    async def get_attendance_by_id(self, request: Request, attendance_id: str, include_image: bool = False):
        """
        Retrieves an attendance record by ID.
        Parameter include_image controls whether the complete base64 image is returned.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_attendance_by_id",
            "target_attendance_id": attendance_id,
            "ip_address": request.client.host
        }
        
        return await self.attendance_use_cases.get_attendance_by_id(
            attendance_id, 
            include_image, 
            audit_data
        )

    async def update_attendance(self, request: Request, attendance_id: str, attendance: UpdateAttendance):
        """
        Updates information of an attendance record.
        Professionals can only update their own records.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "update_attendance",
            "target_attendance_id": attendance_id,
            "ip_address": request.client.host
        }
        
        professional_id = request.state.user.get("user_id")
        
        return await self.attendance_use_cases.update_attendance(
            attendance_id, 
            attendance, 
            professional_id, 
            audit_data
        )

    async def delete_attendance(self, request: Request, attendance_id: str):
        """
        Removes an attendance record.
        Professionals can only remove their own records.
        Administrators can remove any record from their units.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "delete_attendance",
            "target_attendance_id": attendance_id,
            "ip_address": request.client.host
        }
        
        professional_id = request.state.user.get("user_id")
        
        return await self.attendance_use_cases.delete_attendance(
            attendance_id,
            professional_id,
            audit_data
        )
        
    async def get_statistics(self, request: Request, start_date: str, end_date: str):
        """
        Gets statistics on model usage and accuracy for a specific date range.
        Only administrators can access these statistics.
        """
        await self.auth_middleware.verify_request(request)
        
        audit_data = {
            "user_id": request.state.user.get("user_id"),
            "action": "get_statistics",
            "start_date": start_date,
            "end_date": end_date,
            "ip_address": request.client.host
        }
        

        try:
            from datetime import datetime
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            logger.error(f"Invalid date format: start_date={start_date}, end_date={end_date}")
            return {
                "detail": {
                    "message": "Dates must be in YYYY-MM-DD format",
                    "status_code": 400
                }
            }
        
        user_profile = request.state.user.get("profile")
        if user_profile not in ["administrator", "general_administrator"]:
            logger.warning(f"User {audit_data['user_id']} attempted to access statistics without admin privileges")
            return {
                "detail": {
                    "message": "Only administrators can access statistics",
                    "status_code": 403
                }
            }
        
        admin_id = request.state.user.get("user_id")
        

        is_general_admin = (user_profile == "general_administrator")
        
        return await self.attendance_use_cases.get_statistics(
            admin_id,
            start_date,
            end_date,
            is_general_admin,
            audit_data
        )
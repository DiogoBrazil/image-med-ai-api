from fastapi import HTTPException
from ..utils.logger import get_logger
from ..interfaces.create_attendance import CreateAttendance
from ..interfaces.update_attendance import UpdateAttendance
from ..repositories.attendance_repository import AttendanceRepository
from ..repositories.user_repository import UserRepository
from ..repositories.health_unit_repository import HealthUnitRepository
from ..utils.error_handler import raise_http_error
from src.config.settings import Settings

settings = Settings()
logger = get_logger(__name__)

class AttendanceUseCases:
    def __init__(self):
        self.attendance_repository = AttendanceRepository()
        self.user_repository = UserRepository()
        self.health_unit_repository = HealthUnitRepository()
    
    async def add_attendance(self, attendance: CreateAttendance, professional_id: str, audit_data=None):
        """Add a new attendance record with medical prediction results."""
        try:            
            professional = await self.user_repository.get_user_by_id(professional_id)
            if not professional:
                logger.error(f"Error adding attendance: Professional with ID {professional_id} not found")
                raise_http_error(404, "Professional not found")
            
            admin_id = professional.get("admin_id")
            if not admin_id:
                logger.error(f"Error adding attendance: Professional with ID {professional_id} has no admin_id")
                raise_http_error(400, "Professional is not associated with an administrator")
            
            attendance_data = attendance.dict()
            
            health_unit_id = attendance_data.get("health_unit_id")
            if not health_unit_id:
                logger.error("Error adding attendance: Health unit ID is required")
                raise_http_error(400, "Health unit ID is required")
                
            health_unit = await self.health_unit_repository.get_health_unit_by_id(health_unit_id)
            if not health_unit:
                logger.error(f"Error adding attendance: Health unit with ID {health_unit_id} not found")
                raise_http_error(404, "Health unit not found")
                
            if health_unit["admin_id"] != admin_id:
                logger.error(f"Error adding attendance: Health unit belongs to a different administrator")
                raise_http_error(403, "Health unit belongs to a different administrator")
            
            valid_models = ["respiratory", "tuberculosis", "osteoporosis", "breast"]
            if attendance_data["model_used"] not in valid_models:
                logger.error(f"Error adding attendance: Invalid model '{attendance_data['model_used']}'")
                raise_http_error(422, f"Invalid model. Should be one of: {', '.join(valid_models)}")
            
            if attendance_data["model_used"] == "breast" and "bounding_boxes" in attendance_data:
                for box in attendance_data["bounding_boxes"]:
                    required_box_fields = ["x", "y", "width", "height"]
                    for field in required_box_fields:
                        if field not in box:
                            logger.error(f"Error adding attendance: Missing required field '{field}' in bounding box")
                            raise_http_error(400, f"Missing required field '{field}' in bounding box")
            
            attendance_data["professional_id"] = professional_id
            attendance_data["admin_id"] = admin_id
            
            if not attendance_data.get("image_base64"):
                logger.error("Error adding attendance: Image in base64 format is required")
                raise_http_error(400, "Image in base64 format is required")
                
            result = await self.attendance_repository.add_attendance(attendance_data)
            
            if result["added"]:
                return {
                    "detail": {
                        "message": "Attendance record added successfully",
                        "attendance_id": result["attendance_id"],
                        "status_code": 201
                    }
                }
            else:
                logger.error("Error adding attendance record")
                raise_http_error(500, "Error adding attendance record to database")
                
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Unexpected error when adding attendance: {e}")
            raise_http_error(500, "Unexpected error when adding attendance")
    
    async def get_attendances(self, 
                             admin_id: str = None,
                             health_unit_id: str = None,
                             professional_id: str = None,
                             model_used: str = None,
                             limit: int = 10,
                             offset: int = 0,
                             page: int = 1,
                             per_page: int = 10,
                             audit_data=None):
        """
        Retrieve attendances with optional filtering.
        Only administrators can view attendance lists.
        For administrators with multiple health units, health_unit_id is required.
        """
        try:

            if model_used:
                valid_models = ["respiratory", "tuberculosis", "osteoporosis", "breast"]
                if model_used not in valid_models:
                    logger.error(f"Error retrieving attendances: Invalid model '{model_used}'")
                    raise_http_error(422, f"Invalid model. Should be one of: {', '.join(valid_models)}")
            

            user_id = audit_data.get("user_id") if audit_data else None
            is_general_admin = False
            
            if user_id:
                user = await self.user_repository.get_user_by_id(user_id)
                is_general_admin = user and user.get("profile") == "general_administrator"
            

            if admin_id and not professional_id and not is_general_admin:
                health_units = await self.health_unit_repository.get_health_units(admin_id)
                

                if len(health_units) > 1 and not health_unit_id:
                    logger.error(f"Error retrieving attendances: Administrator with multiple health units must specify health_unit_id")
                    raise_http_error(400, "You have multiple health units. Please specify a health_unit_id to filter attendances.")
            

            total_count = await self.attendance_repository.get_attendances_count(
                admin_id=admin_id,
                health_unit_id=health_unit_id,
                professional_id=professional_id,
                model_used=model_used
            )
            

            attendances = await self.attendance_repository.get_attendances(
                admin_id=admin_id,
                health_unit_id=health_unit_id,
                professional_id=professional_id,
                model_used=model_used,
                limit=limit,
                offset=offset
            )
            

            for attendance in attendances:
                if "image_base64" in attendance:
                    attendance["image_base64"] = attendance["image_base64"][:100] + "..."
            

            total_pages = (total_count + per_page - 1) // per_page
            
            return {
                "detail": {
                    "message": "Attendances retrieved successfully",
                    "attendances": attendances,
                    "pagination": {
                        "total_count": total_count,
                        "total_pages": total_pages,
                        "current_page": page,
                        "per_page": per_page
                    },
                    "status_code": 200
                }
            }
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error retrieving attendances: {e}")
            raise_http_error(500, "Error retrieving attendances")

    
    async def get_attendance_by_id(self, attendance_id: str, include_image: bool = False, audit_data=None):
        """
        Retrieve an attendance by ID.
        If include_image is False, the base64 image will be truncated.
        """
        try:
            
            attendance = await self.attendance_repository.get_attendance_by_id(attendance_id)
            
            if attendance:
                if not include_image and "image_base64" in attendance:
                    attendance["image_base64"] = attendance["image_base64"][:100] + "..."
                
                return {
                    "detail": {
                        "message": "Attendance retrieved successfully",
                        "attendance": attendance,
                        "status_code": 200
                    }
                }
            else:
                logger.error(f"Attendance with ID {attendance_id} not found")
                raise_http_error(404, "Attendance not found")
                
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error retrieving attendance: {e}")
            raise_http_error(500, "Error retrieving attendance")

    
    async def update_attendance(self, attendance_id: str, attendance: UpdateAttendance, professional_id: str, audit_data=None):
        """Update attendance information."""
        try:
            
            existing_attendance = await self.attendance_repository.get_attendance_by_id(attendance_id)
            if not existing_attendance:
                logger.error(f"Error updating attendance: Attendance with ID {attendance_id} not found")
                raise_http_error(404, "Attendance not found")
            
            professional = await self.user_repository.get_user_by_id(professional_id)
            if not professional:
                logger.error(f"Error updating attendance: Professional with ID {professional_id} not found")
                raise_http_error(404, "Professional not found")
            
            if (professional["id"] != existing_attendance["professional_id"] and 
                professional["profile"] != "administrator"):
                logger.error(f"Error updating attendance: User with ID {professional_id} does not have permission")
                raise_http_error(403, "You do not have permission to update this attendance")
            
            attendance_data = attendance.dict(exclude_unset=True)
            
            if "model_used" in attendance_data:
                valid_models = ["respiratory", "tuberculosis", "osteoporosis", "breast"]
                if attendance_data["model_used"] not in valid_models:
                    logger.error(f"Error updating attendance: Invalid model '{attendance_data['model_used']}'")
                    raise_http_error(422, f"Invalid model. Should be one of: {', '.join(valid_models)}")
            
            if "bounding_boxes" in attendance_data:
                if existing_attendance["model_used"] != "breast" and "model_used" not in attendance_data:
                    logger.error("Error updating attendance: Bounding boxes only allowed for breast cancer model")
                    raise_http_error(400, "Bounding boxes can only be added to breast cancer model attendances")
                
                for box in attendance_data["bounding_boxes"]:
                    required_box_fields = ["x", "y", "width", "height"]
                    for field in required_box_fields:
                        if field not in box:
                            logger.error(f"Error updating attendance: Missing required field '{field}' in bounding box")
                            raise_http_error(400, f"Missing required field '{field}' in bounding box")
            
            result = await self.attendance_repository.update_attendance(attendance_id, attendance_data)
            
            if result["updated"]:
                return {
                    "detail": {
                        "message": "Attendance updated successfully",
                        "attendance_id": attendance_id,
                        "status_code": 200
                    }
                }
            else:
                logger.error(f"Failed to update attendance with ID {attendance_id}")
                raise_http_error(500, "Failed to update attendance")
                
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error updating attendance: {e}")
            raise_http_error(500, "Error updating attendance")

    
    async def delete_attendance(self, attendance_id: str, professional_id: str, audit_data=None):
        """Delete an attendance by ID."""
        try:            
            existing_attendance = await self.attendance_repository.get_attendance_by_id(attendance_id)
            if not existing_attendance:
                logger.error(f"Error deleting attendance: Attendance with ID {attendance_id} not found")
                raise_http_error(404, "Attendance not found")
            
            professional = await self.user_repository.get_user_by_id(professional_id)
            if not professional:
                logger.error(f"Error deleting attendance: Professional with ID {professional_id} not found")
                raise_http_error(404, "Professional not found")
            
            if (professional["id"] != existing_attendance["professional_id"] and 
                professional["profile"] != "administrator"):
                logger.error(f"Error deleting attendance: User with ID {professional_id} does not have permission")
                raise_http_error(403, "You do not have permission to delete this attendance")
            
            result = await self.attendance_repository.delete_attendance(attendance_id)
            
            if result["deleted"]:
                logger.info(f"Attendance with ID {attendance_id} deleted successfully")
                return {
                    "detail": {
                        "message": "Attendance deleted successfully",
                        "attendance_id": attendance_id,
                        "status_code": 200
                    }
                }
            else:
                logger.error(f"Failed to delete attendance with ID {attendance_id}")
                raise_http_error(500, "Failed to delete attendance")
                
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error deleting attendance: {e}")
            raise_http_error(500, "Error deleting attendance")
    
    async def get_statistics(self, admin_id: str, start_date: str, end_date: str, is_general_admin: bool = False, audit_data=None):
        """
        Get statistics about model usage and accuracy for a specific date range.
        For general_administrator, statistics include all attendances across the system.
        For regular administrators, statistics include only their own attendances.
        
        Parameters:
        - start_date: Start date in YYYY-MM-DD format
        - end_date: End date in YYYY-MM-DD format
        """
        try:
            admin = await self.user_repository.get_user_by_id(admin_id)
            if not admin:
                logger.error(f"Error retrieving statistics: Admin with ID {admin_id} not found")
                raise_http_error(404, "Administrator not found")
            

            statistics_admin_id = None if is_general_admin else admin_id
            statistics = await self.attendance_repository.get_statistics(statistics_admin_id, start_date, end_date)
            

            message = statistics.get("message", "Statistics retrieved successfully")
            

            status_code = 204 if "No model usage found" in message else 200
            
            return {
                "detail": {
                    "message": message,
                    "statistics": statistics,
                    "status_code": status_code
                }
            }
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error retrieving statistics: {e}")
            raise_http_error(500, "Error retrieving statistics")
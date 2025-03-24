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

class AttendanceService:
    def __init__(self):
        self.attendance_repository = AttendanceRepository()
        self.user_repository = UserRepository()
        self.health_unit_repository = HealthUnitRepository()
    
    async def add_attendance(self, attendance: CreateAttendance, professional_id: str, audit_data=None):
        """Add a new attendance record with medical prediction results."""
        try:            
            # Verificar se o profissional existe e é um profissional
            professional = await self.user_repository.get_user_by_id(professional_id)
            if not professional:
                logger.error(f"Error adding attendance: Professional with ID {professional_id} not found")
                raise_http_error(404, "Professional not found")
                
            if professional["profile"] != "professional":
                logger.error(f"Error adding attendance: User with ID {professional_id} is not a professional")
                raise_http_error(403, "User is not a healthcare professional")
            
            # Verificar se o admin_id existe
            admin_id = professional.get("admin_id")
            if not admin_id:
                logger.error(f"Error adding attendance: Professional with ID {professional_id} has no admin_id")
                raise_http_error(400, "Professional is not associated with an administrator")
            
            # Extrair dados do atendimento
            attendance_data = attendance.dict()
            
            # Verificar se a unidade de saúde existe e pertence ao mesmo admin
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
            
            # Validar modelo
            valid_models = ["respiratory", "tuberculosis", "osteoporosis", "breast"]
            if attendance_data["model_used"] not in valid_models:
                logger.error(f"Error adding attendance: Invalid model '{attendance_data['model_used']}'")
                raise_http_error(422, f"Invalid model. Should be one of: {', '.join(valid_models)}")
            
            # Validar bounding boxes para modelo de câncer de mama
            if attendance_data["model_used"] == "breast" and "bounding_boxes" in attendance_data:
                for box in attendance_data["bounding_boxes"]:
                    required_box_fields = ["x", "y", "width", "height"]
                    for field in required_box_fields:
                        if field not in box:
                            logger.error(f"Error adding attendance: Missing required field '{field}' in bounding box")
                            raise_http_error(400, f"Missing required field '{field}' in bounding box")
            
            # Adicionar profissional e admin aos dados
            attendance_data["professional_id"] = professional_id
            attendance_data["admin_id"] = admin_id
            
            # Requisito obrigatório: imagem em base64
            if not attendance_data.get("image_base64"):
                logger.error("Error adding attendance: Image in base64 format is required")
                raise_http_error(400, "Image in base64 format is required")
                
            # Adicionar atendimento
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
                             limit: int = 100,
                             offset: int = 0,
                             audit_data=None):
        """
        Retrieve attendances with optional filtering.
        """
        try:
            # Validar o modelo se for fornecido
            if model_used:
                valid_models = ["respiratory", "tuberculosis", "osteoporosis", "breast"]
                if model_used not in valid_models:
                    logger.error(f"Error retrieving attendances: Invalid model '{model_used}'")
                    raise_http_error(422, f"Invalid model. Should be one of: {', '.join(valid_models)}")
            
            # Buscar atendimentos
            attendances = await self.attendance_repository.get_attendances(
                admin_id=admin_id,
                health_unit_id=health_unit_id,
                professional_id=professional_id,
                model_used=model_used,
                limit=limit,
                offset=offset
            )
            
            # Para cada atendimento, remover a imagem base64 (para reduzir o tamanho da resposta)
            for attendance in attendances:
                if "image_base64" in attendance:
                    # Manter apenas os primeiros 100 caracteres para identificação
                    attendance["image_base64"] = attendance["image_base64"][:100] + "..."
            
            return {
                "detail": {
                    "message": "Attendances retrieved successfully",
                    "attendances": attendances,
                    "count": len(attendances),
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
                # Truncar a imagem base64 se não for solicitada completa
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
            
            # Verificar se o atendimento existe
            existing_attendance = await self.attendance_repository.get_attendance_by_id(attendance_id)
            if not existing_attendance:
                logger.error(f"Error updating attendance: Attendance with ID {attendance_id} not found")
                raise_http_error(404, "Attendance not found")
            
            # Verificar se o profissional tem permissão (é o mesmo profissional ou é um admin)
            professional = await self.user_repository.get_user_by_id(professional_id)
            if not professional:
                logger.error(f"Error updating attendance: Professional with ID {professional_id} not found")
                raise_http_error(404, "Professional not found")
            
            # Se não for o mesmo profissional nem um admin, não tem permissão
            if (professional["id"] != existing_attendance["professional_id"] and 
                professional["profile"] != "administrator"):
                logger.error(f"Error updating attendance: User with ID {professional_id} does not have permission")
                raise_http_error(403, "You do not have permission to update this attendance")
            
            # Extrair dados da atualização
            attendance_data = attendance.dict(exclude_unset=True)
            
            # Validar modelo se for atualizado
            if "model_used" in attendance_data:
                valid_models = ["respiratory", "tuberculosis", "osteoporosis", "breast"]
                if attendance_data["model_used"] not in valid_models:
                    logger.error(f"Error updating attendance: Invalid model '{attendance_data['model_used']}'")
                    raise_http_error(422, f"Invalid model. Should be one of: {', '.join(valid_models)}")
            
            # Validar bounding boxes para modelo de câncer de mama
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
            
            # Atualizar atendimento
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
            # Verificar se o atendimento existe
            existing_attendance = await self.attendance_repository.get_attendance_by_id(attendance_id)
            if not existing_attendance:
                logger.error(f"Error deleting attendance: Attendance with ID {attendance_id} not found")
                raise_http_error(404, "Attendance not found")
            
            # Verificar se o profissional tem permissão (é o mesmo profissional ou é um admin)
            professional = await self.user_repository.get_user_by_id(professional_id)
            if not professional:
                logger.error(f"Error deleting attendance: Professional with ID {professional_id} not found")
                raise_http_error(404, "Professional not found")
            
            # Se não for o mesmo profissional nem um admin, não tem permissão
            if (professional["id"] != existing_attendance["professional_id"] and 
                professional["profile"] != "administrator"):
                logger.error(f"Error deleting attendance: User with ID {professional_id} does not have permission")
                raise_http_error(403, "You do not have permission to delete this attendance")
            
            # Deletar atendimento
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
    
    async def get_statistics(self, admin_id: str, period: str = "month", audit_data=None):
        """
        Get statistics about model usage and accuracy for an admin.
        Period can be 'day', 'week', 'month', 'year'.
        """
        try:
            # Verificar se o admin existe
            admin = await self.user_repository.get_user_by_id(admin_id)
            if not admin:
                logger.error(f"Error retrieving statistics: Admin with ID {admin_id} not found")
                raise_http_error(404, "Administrator not found")
            
            # Validar período
            valid_periods = ["day", "week", "month", "year"]
            if period not in valid_periods:
                logger.error(f"Error retrieving statistics: Invalid period '{period}'")
                raise_http_error(422, f"Invalid period. Should be one of: {', '.join(valid_periods)}")
            
            # Buscar estatísticas
            statistics = await self.attendance_repository.get_statistics(admin_id, period)
            
            return {
                "detail": {
                    "message": "Statistics retrieved successfully",
                    "statistics": statistics,
                    "status_code": 200
                }
            }
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Error retrieving statistics: {e}")
            raise_http_error(500, "Error retrieving statistics")
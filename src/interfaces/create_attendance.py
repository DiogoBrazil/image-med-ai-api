from pydantic import BaseModel

class CreateAttendance(BaseModel):
    professional_id: str
    health_unit_id: str
    admin_id: str
    model_used: str
    model_result: str
    expected_result: str
    correct_diagnosis: bool
    image_base64: str
    observation: str

from pydantic import BaseModel

class UpdateAttendance(BaseModel):
    professional_id: str
    health_unit_id: str
    admin_id: str
    model_used: str
    model_result: str
    expected_result: str
    correct_diagnosis: bool
    observation: str

from pydantic import BaseModel, field_validator
from datetime import datetime

class CreateSubscriptions(BaseModel):
    admin_id: str
    start_date: str
    end_date: str
    status: str = "active"
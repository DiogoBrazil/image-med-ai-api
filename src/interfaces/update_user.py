from pydantic import BaseModel

class UpdateUser(BaseModel):
    full_name: str
    email: str
    profile: str
    status: str

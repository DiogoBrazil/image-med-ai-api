from pydantic import BaseModel

class CreateUser(BaseModel):
    full_name: str
    email: str
    password: str
    profile: str
    status: str

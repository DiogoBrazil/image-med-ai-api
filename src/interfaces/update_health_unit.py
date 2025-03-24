from pydantic import BaseModel

class UpdateHealthUnit(BaseModel):
    admin_id: str
    name: str
    cnpj: str
    status: str

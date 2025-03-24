from pydantic import BaseModel

class CreateHealthUnit(BaseModel):
    admin_id: str
    name: str
    cnpj: str
    status: str

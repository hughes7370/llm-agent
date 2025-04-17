# from common.data_model import BaseModel

# NOTE: Overiding to use pydantic v2 with latest fastapi
from pydantic import BaseModel as PydanticBaseModel

class BaseModel(PydanticBaseModel):
    """Base model for all data models"""
    class Config:
        populate_by_name = True
        validate_assignment = True
        arbitrary_types_allowed = True
        protected_namespaces = ()

class HealthResponse(BaseModel):
    """Represents the health response"""
    alive: bool



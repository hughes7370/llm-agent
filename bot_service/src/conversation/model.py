from common.data_model import Roles, PlannerEnum
# from common.data_model import BaseModel

# NOTE: Overiding to use pydantic v2 with latest fastapi
from pydantic import BaseModel as PydanticBaseModel, ConfigDict

class BaseModel(PydanticBaseModel):
    """Base model for all data models"""
    class Config:
        populate_by_name = True
        validate_assignment = True
        arbitrary_types_allowed = True
        protected_namespaces = ()
        model_config = ConfigDict(use_enum_values=True)

class HealthResponse(BaseModel):
    """Represents the health response"""
    alive: bool

class ConversationRequest(BaseModel):
    """Represents the conversation request request"""
    query: str
    user_role: Roles = Roles.admin.value
    context_id: str | None = None
    planner: PlannerEnum = PlannerEnum.planner_with_apis.value

class ConversationResponse(BaseModel):
    """Represents the conversation response request"""
    context_id: int
    response: str
    response_time_in_seconds: float 
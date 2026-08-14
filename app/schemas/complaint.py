from datetime import datetime

from pydantic import BaseModel, Field


class ComplaintCreate(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10)
    category: str
    priority: str = "medium"


class ComplaintResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    priority: str
    status: str
    citizen_id: int
    assigned_authority_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }
class ComplaintStatusUpdate(BaseModel):
    status: str
    
class ComplaintAssignment(BaseModel):
    authority_id: int
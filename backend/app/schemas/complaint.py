from datetime import datetime
from pydantic import BaseModel, ConfigDict

from pydantic import BaseModel, Field
from typing import Literal


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
    status: Literal[
        "pending",
        "assigned",
        "in_progress",
        "resolved",
    ]
    
class ComplaintAssignment(BaseModel):
    authority_id: int

class ComplaintHistoryResponse(BaseModel):
    id: int
    complaint_id: int
    status: str
    changed_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
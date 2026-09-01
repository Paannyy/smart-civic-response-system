from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict


class AttachmentResponse(BaseModel):
    id: int
    complaint_id: int
    uploaded_by: int
    original_filename: str
    content_type: str
    file_size: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttachmentListResponse(BaseModel):
    items: List[AttachmentResponse]
    total: int

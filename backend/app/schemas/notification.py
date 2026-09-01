from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    complaint_id: Optional[int]
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class PaginatedNotificationResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int
    limit: int
    offset: int

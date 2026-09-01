from typing import Dict, Optional
from pydantic import BaseModel, ConfigDict


class AnalyticsResponse(BaseModel):
    total_complaints: int
    pending_complaints: int
    assigned_complaints: int
    in_progress_complaints: int
    resolved_complaints: int
    by_category: Dict[str, int]
    by_department: Dict[str, int]
    avg_resolution_time_seconds: Optional[float]
    avg_resolution_time_by_department: Dict[str, float]

    model_config = ConfigDict(from_attributes=True)

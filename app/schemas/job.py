from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict
from app.models.job import JobStatus, ProcessingType


class ProcessingJobCreate(BaseModel):
    document_id: int
    processing_type: Optional[str] = "auto"
    extraction_configuration: Optional[Dict[str, Any]] = None


class ProcessingLogResponse(BaseModel):
    id: int
    log_level: str
    event_type: str
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProcessingJobResponse(BaseModel):
    id: int
    document_id: int
    document_name: Optional[str] = None
    created_by: int
    processing_type: str
    status: JobStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_duration: Optional[float] = None
    retry_count: int
    error_summary: Optional[str] = None
    created_at: datetime
    logs: Optional[List[ProcessingLogResponse]] = None

    model_config = ConfigDict(from_attributes=True)

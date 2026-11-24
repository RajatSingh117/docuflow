from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.document import UploadStatus


class DocumentBase(BaseModel):
    original_filename: str
    file_type: str
    file_size: int
    checksum: str
    upload_status: UploadStatus = UploadStatus.STORED


class DocumentCreate(DocumentBase):
    stored_filename: str
    storage_reference: str


class DocumentResponse(DocumentBase):
    id: int
    uploaded_by: int
    uploader_name: Optional[str] = None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)

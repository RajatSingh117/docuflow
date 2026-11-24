import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class UploadStatus(str, enum.Enum):
    PENDING = "pending"
    STORED = "stored"
    FAILED = "failed"
    REJECTED = "rejected"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), unique=True, nullable=False)
    file_type = Column(String(50), nullable=False, index=True)  # pdf, csv, xlsx, png, jpg, tiff
    file_size = Column(BigInteger, nullable=False)
    checksum = Column(String(64), index=True, nullable=False)  # SHA-256
    storage_reference = Column(String(500), nullable=False)
    upload_status = Column(Enum(UploadStatus), default=UploadStatus.STORED, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    uploader = relationship("User", back_populates="documents")
    processing_jobs = relationship("ProcessingJob", back_populates="document", cascade="all, delete-orphan")

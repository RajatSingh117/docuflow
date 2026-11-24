import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base, utc_now


class JobStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ProcessingType(str, enum.Enum):
    PDF_DIGITAL = "pdf_digital"
    OCR_SCANNED = "ocr_scanned"
    IMAGE = "image"
    CSV = "csv"
    EXCEL = "excel"
    AUTO = "auto"


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    processing_type = Column(String(50), default="auto", nullable=False)
    extraction_configuration = Column(JSON, nullable=True)  # configured fields to extract
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    processing_duration = Column(Float, nullable=True)  # in seconds
    retry_count = Column(Integer, default=0, nullable=False)
    error_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    # Relationships
    document = relationship("Document", back_populates="processing_jobs")
    creator = relationship("User", back_populates="processing_jobs")
    extracted_records = relationship("ExtractedRecord", back_populates="job", cascade="all, delete-orphan")
    logs = relationship("ProcessingLog", back_populates="job", cascade="all, delete-orphan")
    reports = relationship("GeneratedReport", back_populates="job", cascade="all, delete-orphan")
    executions = relationship("ScheduledJobExecution", back_populates="processing_job")


class ProcessingLog(Base):
    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True, index=True)
    processing_job_id = Column(Integer, ForeignKey("processing_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    log_level = Column(String(20), default="INFO", nullable=False)  # INFO, WARNING, ERROR
    event_type = Column(String(50), nullable=False)  # EXTRACTION_STARTED, VALIDATION_FAILED, etc.
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    # Relationships
    job = relationship("ProcessingJob", back_populates="logs")

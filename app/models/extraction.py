import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base, utc_now


class ValidationStatus(str, enum.Enum):
    VALID = "VALID"
    WARNING = "WARNING"
    INVALID = "INVALID"
    MISSING = "MISSING"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ExtractedRecord(Base):
    __tablename__ = "extracted_records"

    id = Column(Integer, primary_key=True, index=True)
    processing_job_id = Column(Integer, ForeignKey("processing_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    record_number = Column(Integer, default=1, nullable=False)
    extracted_data = Column(JSON, nullable=False)  # Dictionary of raw/normalized fields
    validation_status = Column(Enum(ValidationStatus), default=ValidationStatus.NEEDS_REVIEW, nullable=False, index=True)
    confidence_score = Column(Float, default=1.0, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    job = relationship("ProcessingJob", back_populates="extracted_records")
    fields = relationship("ExtractedField", back_populates="record", cascade="all, delete-orphan")
    validation_results = relationship("ValidationResult", back_populates="record", cascade="all, delete-orphan")


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id = Column(Integer, primary_key=True, index=True)
    extracted_record_id = Column(Integer, ForeignKey("extracted_records.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    extracted_value = Column(Text, nullable=True)
    normalized_value = Column(Text, nullable=True)
    confidence_score = Column(Float, default=1.0, nullable=False)
    extraction_source = Column(String(50), default="regex", nullable=False)  # regex, ocr, table, manual
    validation_status = Column(Enum(ValidationStatus), default=ValidationStatus.VALID, nullable=False)
    validation_message = Column(String(500), nullable=True)

    # Relationships
    record = relationship("ExtractedRecord", back_populates="fields")

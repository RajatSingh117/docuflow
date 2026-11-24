from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base, utc_now


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True, index=True)
    extracted_record_id = Column(Integer, ForeignKey("extracted_records.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False)
    validation_rule = Column(String(100), nullable=False)  # required, email_format, date_format, etc.
    status = Column(String(50), nullable=False)  # VALID, WARNING, INVALID, MISSING
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    record = relationship("ExtractedRecord", back_populates="validation_results")

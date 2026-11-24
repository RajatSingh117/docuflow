from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    schedule_type = Column(String(50), nullable=False)  # daily, weekly, monthly
    schedule_configuration = Column(JSON, nullable=True)  # cron details, target file type, etc.
    is_active = Column(Boolean, default=True, nullable=False)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = relationship("User", back_populates="scheduled_jobs")
    executions = relationship("ScheduledJobExecution", back_populates="scheduled_job", cascade="all, delete-orphan")


class ScheduledJobExecution(Base):
    __tablename__ = "scheduled_job_executions"

    id = Column(Integer, primary_key=True, index=True)
    scheduled_job_id = Column(Integer, ForeignKey("scheduled_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    processing_job_id = Column(Integer, ForeignKey("processing_jobs.id", ondelete="SET NULL"), nullable=True)
    execution_status = Column(String(50), default="SUCCESS", nullable=False)  # SUCCESS, FAILED
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error_summary = Column(Text, nullable=True)

    # Relationships
    scheduled_job = relationship("ScheduledJob", back_populates="executions")
    processing_job = relationship("ProcessingJob", back_populates="executions")

import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from app.database import Base, utc_now


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PROCESSING_MANAGER = "processing_manager"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    documents = relationship("Document", back_populates="uploader", cascade="all, delete-orphan")
    processing_jobs = relationship("ProcessingJob", back_populates="creator", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    scheduled_jobs = relationship("ScheduledJob", back_populates="creator")

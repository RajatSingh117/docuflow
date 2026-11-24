from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.document import Document
from app.models.job import ProcessingJob, JobStatus
from app.models.extraction import ExtractedRecord, ExtractedField, ValidationStatus


def get_dashboard_metrics(db: Session) -> Dict[str, Any]:
    """Calculate live dashboard KPIs directly from database records without mock data."""
    # 1. Total Documents Uploaded
    total_docs = db.query(func.count(Document.id)).scalar() or 0

    # 2. Successfully Processed Jobs
    success_jobs = db.query(func.count(ProcessingJob.id)).filter(
        ProcessingJob.status == JobStatus.COMPLETED
    ).scalar() or 0

    # 3. Processing in Progress
    in_progress_jobs = db.query(func.count(ProcessingJob.id)).filter(
        ProcessingJob.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING])
    ).scalar() or 0

    # 4. Failed Jobs
    failed_jobs = db.query(func.count(ProcessingJob.id)).filter(
        ProcessingJob.status == JobStatus.FAILED
    ).scalar() or 0

    # 5. Documents Awaiting Review
    awaiting_review = db.query(func.count(ProcessingJob.id)).filter(
        ProcessingJob.status == JobStatus.NEEDS_REVIEW
    ).scalar() or 0

    # 6. Average Processing Time
    avg_time_val = db.query(func.avg(ProcessingJob.processing_duration)).filter(
        ProcessingJob.status == JobStatus.COMPLETED,
        ProcessingJob.processing_duration.isnot(None)
    ).scalar()
    avg_processing_time = round(float(avg_time_val), 2) if avg_time_val is not None else 0.0

    # Success vs Failure breakdown
    total_eligible = success_jobs + failed_jobs
    success_rate = round((success_jobs / total_eligible * 100), 1) if total_eligible > 0 else 0.0
    failure_rate = round((failed_jobs / total_eligible * 100), 1) if total_eligible > 0 else 0.0

    # File type distribution
    file_types = db.query(
        Document.file_type, func.count(Document.id)
    ).group_by(Document.file_type).all()
    file_type_dist = {ft: count for ft, count in file_types}

    # Processing status distribution
    statuses = db.query(
        ProcessingJob.status, func.count(ProcessingJob.id)
    ).group_by(ProcessingJob.status).all()
    status_dist = {s.value if hasattr(s, "value") else str(s): count for s, count in statuses}

    # Recent Documents
    recent_docs = db.query(Document).order_by(Document.uploaded_at.desc()).limit(10).all()

    # Recent Processing Jobs
    recent_jobs = db.query(ProcessingJob).order_by(ProcessingJob.created_at.desc()).limit(10).all()

    return {
        "total_documents": total_docs,
        "successfully_processed": success_jobs,
        "processing_in_progress": in_progress_jobs,
        "failed_jobs": failed_jobs,
        "awaiting_review": awaiting_review,
        "average_processing_time": avg_processing_time,
        "success_rate": success_rate,
        "failure_rate": failure_rate,
        "file_type_distribution": file_type_dist,
        "status_distribution": status_dist,
        "recent_documents": recent_docs,
        "recent_jobs": recent_jobs,
    }

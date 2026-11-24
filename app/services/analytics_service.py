from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.models.document import Document
from app.models.job import ProcessingJob, JobStatus
from app.models.extraction import ExtractedRecord, ExtractedField, ValidationStatus
from app.models.report import GeneratedReport


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


def get_detailed_analytics(db: Session) -> Dict[str, Any]:
    """Calculate in-depth operational analytics, performance per file type, and report metrics."""
    base_metrics = get_dashboard_metrics(db)

    # 1. Performance breakdown by File Type
    # Join ProcessingJob with Document
    type_stats_query = (
        db.query(
            Document.file_type,
            func.count(ProcessingJob.id).label("total_jobs"),
            func.sum(case((ProcessingJob.status == JobStatus.COMPLETED, 1), else_=0)).label("completed"),
            func.sum(case((ProcessingJob.status == JobStatus.FAILED, 1), else_=0)).label("failed"),
            func.avg(case((ProcessingJob.status == JobStatus.COMPLETED, ProcessingJob.processing_duration), else_=None)).label("avg_duration")
        )
        .join(ProcessingJob, ProcessingJob.document_id == Document.id)
        .group_by(Document.file_type)
        .all()
    )

    by_file_type = []
    for ft, total, comp, fail, avg_dur in type_stats_query:
        comp_count = int(comp or 0)
        fail_count = int(fail or 0)
        tot_eligible = comp_count + fail_count
        succ_pct = round((comp_count / tot_eligible * 100), 1) if tot_eligible > 0 else 0.0
        by_file_type.append({
            "file_type": ft.upper(),
            "total_jobs": total,
            "completed": comp_count,
            "failed": fail_count,
            "success_rate": succ_pct,
            "avg_duration": round(float(avg_dur), 2) if avg_dur is not None else 0.0
        })

    # 2. Field Confidence Statistics
    total_fields = db.query(func.count(ExtractedField.id)).scalar() or 0
    avg_confidence = db.query(func.avg(ExtractedField.confidence_score)).scalar()
    high_conf = db.query(func.count(ExtractedField.id)).filter(ExtractedField.confidence_score >= 0.85).scalar() or 0
    med_conf = db.query(func.count(ExtractedField.id)).filter(
        ExtractedField.confidence_score >= 0.60,
        ExtractedField.confidence_score < 0.85
    ).scalar() or 0
    low_conf = db.query(func.count(ExtractedField.id)).filter(ExtractedField.confidence_score < 0.60).scalar() or 0

    confidence_stats = {
        "total_fields": total_fields,
        "avg_confidence": round(float(avg_confidence), 3) if avg_confidence is not None else 0.0,
        "high_confidence_count": high_conf,
        "medium_confidence_count": med_conf,
        "low_confidence_count": low_conf,
        "high_confidence_pct": round((high_conf / total_fields * 100), 1) if total_fields > 0 else 0.0,
    }

    # 3. Validation Breakdown
    valid_count = db.query(func.count(ExtractedField.id)).filter(ExtractedField.validation_status == ValidationStatus.VALID).scalar() or 0
    invalid_count = db.query(func.count(ExtractedField.id)).filter(ExtractedField.validation_status == ValidationStatus.INVALID).scalar() or 0
    warning_count = db.query(func.count(ExtractedField.id)).filter(ExtractedField.validation_status == ValidationStatus.WARNING).scalar() or 0
    review_count = db.query(func.count(ExtractedField.id)).filter(ExtractedField.validation_status.in_([ValidationStatus.NEEDS_REVIEW, ValidationStatus.MISSING])).scalar() or 0

    validation_stats = {
        "valid": valid_count,
        "invalid": invalid_count,
        "warning": warning_count,
        "needs_review": review_count,
        "accuracy_rate": round((valid_count / total_fields * 100), 1) if total_fields > 0 else 0.0
    }

    # 4. Report Generation Metrics
    total_reports = db.query(func.count(GeneratedReport.id)).scalar() or 0
    excel_reports = db.query(func.count(GeneratedReport.id)).filter(GeneratedReport.report_type == "excel").scalar() or 0
    pdf_reports = db.query(func.count(GeneratedReport.id)).filter(GeneratedReport.report_type == "pdf").scalar() or 0

    report_stats = {
        "total_reports": total_reports,
        "excel_reports": excel_reports,
        "pdf_reports": pdf_reports,
    }

    return {
        **base_metrics,
        "by_file_type": by_file_type,
        "confidence_stats": confidence_stats,
        "validation_stats": validation_stats,
        "report_stats": report_stats
    }

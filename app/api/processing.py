from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import ProcessingJob, JobStatus, ProcessingLog
from app.models.document import Document
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas.job import ProcessingJobCreate, ProcessingJobResponse, ProcessingLogResponse
from app.api.deps import require_manager_or_admin, require_any_authenticated
from app.services.processing_service import ProcessingService

router = APIRouter(prefix="/api/processing", tags=["Processing"])


@router.get("/jobs", response_model=List[ProcessingJobResponse])
def list_processing_jobs(
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    document_id: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db)
):
    """List document processing jobs with optional filtering."""
    query = db.query(ProcessingJob)

    if status_filter:
        query = query.filter(ProcessingJob.status == status_filter)
    if document_id:
        query = query.filter(ProcessingJob.document_id == document_id)

    jobs = query.order_by(ProcessingJob.created_at.desc()).offset(skip).limit(limit).all()

    results = []
    for j in jobs:
        resp = ProcessingJobResponse(
            id=j.id,
            document_id=j.document_id,
            document_name=j.document.original_filename if j.document else "Unknown",
            created_by=j.created_by,
            processing_type=j.processing_type,
            status=j.status,
            started_at=j.started_at,
            completed_at=j.completed_at,
            processing_duration=j.processing_duration,
            retry_count=j.retry_count,
            error_summary=j.error_summary,
            created_at=j.created_at
        )
        results.append(resp)
    return results


@router.post("/jobs", response_model=ProcessingJobResponse, status_code=status.HTTP_201_CREATED)
def create_processing_job(
    job_in: ProcessingJobCreate,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Initiate a new document processing job."""
    doc = db.query(Document).filter(Document.id == job_in.document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target document not found.")

    # Prevent accidental duplicate execution if job is already queued or processing
    active_job = db.query(ProcessingJob).filter(
        ProcessingJob.document_id == doc.id,
        ProcessingJob.status.in_([JobStatus.QUEUED, JobStatus.PROCESSING])
    ).first()
    if active_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An active processing job (#JOB-{active_job.id}) is already {active_job.status.value.lower()} for document '{doc.original_filename}'."
        )

    # Determine processing type if set to auto
    pipeline_type = job_in.processing_type or "auto"
    if pipeline_type == "auto":
        if doc.file_type == "pdf":
            pipeline_type = "pdf_digital"
        elif doc.file_type in ["jpg", "png", "tiff"]:
            pipeline_type = "image"
        elif doc.file_type == "csv":
            pipeline_type = "csv"
        elif doc.file_type == "xlsx":
            pipeline_type = "excel"

    new_job = ProcessingJob(
        document_id=doc.id,
        created_by=current_user.id,
        processing_type=pipeline_type,
        extraction_configuration=job_in.extraction_configuration or {},
        status=JobStatus.QUEUED,
        retry_count=0
    )
    db.add(new_job)
    db.flush()

    # Initial log
    log = ProcessingLog(
        processing_job_id=new_job.id,
        log_level="INFO",
        event_type="JOB_CREATED",
        message=f"Processing job #JOB-{new_job.id} created for document '{doc.original_filename}' with pipeline '{pipeline_type}'."
    )
    db.add(log)

    audit = AuditLog(
        user_id=current_user.id,
        action="JOB_CREATED",
        entity_type="ProcessingJob",
        entity_id=new_job.id,
        new_values={"document_id": doc.id, "pipeline": pipeline_type}
    )
    db.add(audit)
    db.commit()
    db.refresh(new_job)

    # Execute processing pipeline synchronously if in test/standalone mode
    try:
        service = ProcessingService(db)
        completed_job = service.execute_job(new_job.id)
        return ProcessingJobResponse(
            id=completed_job.id,
            document_id=completed_job.document_id,
            document_name=doc.original_filename,
            created_by=completed_job.created_by,
            processing_type=completed_job.processing_type,
            status=completed_job.status,
            started_at=completed_job.started_at,
            completed_at=completed_job.completed_at,
            processing_duration=completed_job.processing_duration,
            retry_count=completed_job.retry_count,
            error_summary=completed_job.error_summary,
            created_at=completed_job.created_at
        )
    except Exception:
        return ProcessingJobResponse(
            id=new_job.id,
            document_id=new_job.document_id,
            document_name=doc.original_filename,
            created_by=new_job.created_by,
            processing_type=new_job.processing_type,
            status=new_job.status,
            started_at=new_job.started_at,
            completed_at=new_job.completed_at,
            processing_duration=new_job.processing_duration,
            retry_count=new_job.retry_count,
            error_summary=new_job.error_summary,
            created_at=new_job.created_at
        )


@router.get("/jobs/{job_id}", response_model=ProcessingJobResponse)
def get_processing_job(
    job_id: int,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db)
):
    """Retrieve details and execution logs of a processing job."""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found.")

    logs = [
        ProcessingLogResponse(
            id=l.id,
            log_level=l.log_level,
            event_type=l.event_type,
            message=l.message,
            created_at=l.created_at
        )
        for l in job.logs
    ]

    return ProcessingJobResponse(
        id=job.id,
        document_id=job.document_id,
        document_name=job.document.original_filename if job.document else "Unknown",
        created_by=job.created_by,
        processing_type=job.processing_type,
        status=job.status,
        started_at=job.started_at,
        completed_at=job.completed_at,
        processing_duration=job.processing_duration,
        retry_count=job.retry_count,
        error_summary=job.error_summary,
        created_at=job.created_at,
        logs=logs
    )


@router.post("/jobs/{job_id}/retry", response_model=ProcessingJobResponse)
def retry_processing_job(
    job_id: int,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Retry an eligible failed processing job."""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found.")

    if job.status not in [JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only failed or cancelled jobs can be retried. Current status: {job.status.value}."
        )

    job.status = JobStatus.QUEUED
    job.retry_count += 1
    job.error_summary = None
    job.started_at = None
    job.completed_at = None

    log = ProcessingLog(
        processing_job_id=job.id,
        log_level="INFO",
        event_type="JOB_RETRIED",
        message=f"Job marked for retry attempt #{job.retry_count} by {current_user.name}."
    )
    db.add(log)

    audit = AuditLog(
        user_id=current_user.id,
        action="JOB_RETRIED",
        entity_type="ProcessingJob",
        entity_id=job.id,
        new_values={"retry_count": job.retry_count}
    )
    db.add(audit)
    db.commit()
    db.refresh(job)

    return ProcessingJobResponse(
        id=job.id,
        document_id=job.document_id,
        document_name=job.document.original_filename if job.document else "Unknown",
        created_by=job.created_by,
        processing_type=job.processing_type,
        status=job.status,
        started_at=job.started_at,
        completed_at=job.completed_at,
        processing_duration=job.processing_duration,
        retry_count=job.retry_count,
        error_summary=job.error_summary,
        created_at=job.created_at
    )

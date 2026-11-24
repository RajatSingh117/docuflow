from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.job import ProcessingJob
from app.api.deps import require_manager_or_admin, require_any_authenticated
from app.services.review_service import ReviewService

router = APIRouter(prefix="/api/reviews", tags=["Review & Approvals"])


class FieldUpdateRequest(BaseModel):
    value: str


class RecordApproveRequest(BaseModel):
    force_override: bool = False


@router.get("/jobs/{job_id}")
def get_job_review_data(
    job_id: int,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db)
):
    """Retrieve all extracted records, fields, and validation results for review."""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    records_data = []
    for rec in job.extracted_records:
        fields_data = [
            {
                "id": f.id,
                "field_name": f.field_name,
                "extracted_value": f.extracted_value,
                "normalized_value": f.normalized_value,
                "confidence_score": f.confidence_score,
                "confidence_percent": int(f.confidence_score * 100),
                "extraction_source": f.extraction_source,
                "validation_status": f.validation_status.value,
                "validation_message": f.validation_message
            }
            for f in rec.fields
        ]

        val_results = [
            {
                "field_name": vr.field_name,
                "rule": vr.validation_rule,
                "status": vr.status,
                "message": vr.message
            }
            for vr in rec.validation_results
        ]

        records_data.append({
            "id": rec.id,
            "record_number": rec.record_number,
            "extracted_data": rec.extracted_data,
            "validation_status": rec.validation_status.value,
            "confidence_score": rec.confidence_score,
            "is_approved": rec.is_approved,
            "fields": fields_data,
            "validation_results": val_results
        })

    return {
        "job_id": job.id,
        "document_name": job.document.original_filename if job.document else "Unknown",
        "status": job.status.value,
        "records": records_data
    }


@router.put("/fields/{field_id}")
def update_field(
    field_id: int,
    req_body: FieldUpdateRequest,
    request: Request,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Edit an extracted field value. Automatically re-validates and logs audit trail."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    service = ReviewService(db)
    field = service.update_field_value(field_id, req_body.value, current_user, client_ip)
    return {
        "id": field.id,
        "field_name": field.field_name,
        "extracted_value": field.extracted_value,
        "normalized_value": field.normalized_value,
        "confidence_score": field.confidence_score,
        "validation_status": field.validation_status.value,
        "validation_message": field.validation_message
    }


@router.post("/records/{record_id}/approve")
def approve_record(
    record_id: int,
    req_body: RecordApproveRequest,
    request: Request,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Approve a single validated record."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    service = ReviewService(db)
    record = service.approve_record(record_id, current_user, req_body.force_override, client_ip)
    return {
        "id": record.id,
        "is_approved": record.is_approved,
        "validation_status": record.validation_status.value
    }


@router.post("/jobs/{job_id}/approve")
def approve_all_job_records(
    job_id: int,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Approve all validated records for a job and advance job to COMPLETED."""
    service = ReviewService(db)
    job = service.approve_job_records(job_id, current_user)
    return {
        "job_id": job.id,
        "status": job.status.value,
        "message": "All records approved successfully. Ready for report generation."
    }

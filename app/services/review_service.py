from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.extraction import ExtractedRecord, ExtractedField, ValidationStatus
from app.models.job import ProcessingJob, JobStatus, ProcessingLog
from app.models.audit import AuditLog
from app.models.validation import ValidationResult
from app.models.user import User
from app.validators import ValidationEngine
from app.extractors.normalizers import normalize_date, normalize_amount, normalize_currency, normalize_phone


class ReviewService:
    """Manages human review, inline corrections, audit logs, and approval workflows."""

    def __init__(self, db: Session):
        self.db = db
        self.validator = ValidationEngine(db)

    def update_field_value(
        self,
        field_id: int,
        new_value: str,
        user: User,
        client_ip: Optional[str] = "127.0.0.1"
    ) -> ExtractedField:
        """Edit an extracted field value, record audit log, and re-run validation."""
        field = self.db.query(ExtractedField).filter(ExtractedField.id == field_id).first()
        if not field:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found.")

        old_val = field.extracted_value
        record = field.record

        # Apply field normalization
        clean_val = str(new_value).strip() if new_value is not None else ""
        norm_val = clean_val
        if field.field_name in ["invoice_date", "due_date", "date"]:
            norm_val = normalize_date(clean_val) or clean_val
        elif field.field_name in ["total_amount", "tax_amount"]:
            amt = normalize_amount(clean_val)
            norm_val = f"{amt:.2f}" if amt is not None else clean_val
        elif field.field_name == "currency":
            norm_val = normalize_currency(clean_val)
        elif field.field_name == "phone":
            norm_val = normalize_phone(clean_val) or clean_val

        # Update field attributes
        field.extracted_value = clean_val
        field.normalized_value = norm_val
        field.confidence_score = 1.0  # Human-verified manual correction gets 1.0 confidence
        field.extraction_source = "manual_correction"

        # Update record JSON dictionary
        rec_data = dict(record.extracted_data or {})
        rec_data[field.field_name] = norm_val
        record.extracted_data = rec_data

        # Re-run validation on the record
        # Clear old validation results for this record
        self.db.query(ValidationResult).filter(ValidationResult.extracted_record_id == record.id).delete()
        val_outcomes = self.validator.validate_record(rec_data, current_record_id=record.id)
        record.validation_status = self.validator.compute_record_status(val_outcomes)

        for vr in val_outcomes:
            new_vr = ValidationResult(
                extracted_record_id=record.id,
                field_name=vr["field_name"],
                validation_rule=vr["rule"],
                status=vr["status"],
                message=vr["message"]
            )
            self.db.add(new_vr)

        # Update field validation status
        match_vr = [v for v in val_outcomes if v["field_name"] == field.field_name]
        if match_vr:
            field.validation_status = ValidationStatus(match_vr[0]["status"])
            field.validation_message = match_vr[0]["message"]
        else:
            field.validation_status = ValidationStatus.VALID
            field.validation_message = None

        # Record Audit Log (user, timestamp, original value, updated value)
        audit = AuditLog(
            user_id=user.id,
            action="FIELD_MANUAL_CORRECTION",
            entity_type="ExtractedField",
            entity_id=field.id,
            old_values={"field": field.field_name, "value": old_val},
            new_values={"field": field.field_name, "value": clean_val, "normalized": norm_val},
            ip_address=client_ip
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(field)
        return field

    def approve_record(
        self,
        record_id: int,
        user: User,
        force_override: bool = False,
        client_ip: Optional[str] = "127.0.0.1"
    ) -> ExtractedRecord:
        """Approve validated record with audit logging and mandatory field check."""
        record = self.db.query(ExtractedRecord).filter(ExtractedRecord.id == record_id).first()
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found.")

        # If invalid mandatory fields remain, block approval unless authorized override is provided
        if record.validation_status in [ValidationStatus.INVALID, ValidationStatus.MISSING]:
            if not force_override:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot approve record with '{record.validation_status.value}' validation status without explicit override."
                )

        record.is_approved = True
        record.updated_at = datetime.utcnow()

        audit = AuditLog(
            user_id=user.id,
            action="RECORD_APPROVED",
            entity_type="ExtractedRecord",
            entity_id=record.id,
            new_values={"is_approved": True, "force_override": force_override},
            ip_address=client_ip
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(record)
        return record

    def approve_job_records(self, job_id: int, user: User) -> ProcessingJob:
        """Approve all valid records for a processing job and mark job COMPLETED."""
        job = self.db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

        for rec in job.extracted_records:
            rec.is_approved = True

        job.status = JobStatus.COMPLETED

        log = ProcessingLog(
            processing_job_id=job.id,
            log_level="INFO",
            event_type="JOB_APPROVED",
            message=f"All records approved by {user.name}. Status updated to COMPLETED."
        )
        self.db.add(log)

        audit = AuditLog(
            user_id=user.id,
            action="JOB_APPROVED",
            entity_type="ProcessingJob",
            entity_id=job.id,
            new_values={"status": "COMPLETED"}
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(job)
        return job

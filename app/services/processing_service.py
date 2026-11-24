import time
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.job import ProcessingJob, JobStatus, ProcessingLog
from app.models.document import Document
from app.models.extraction import ExtractedRecord, ExtractedField, ValidationStatus
from app.models.validation import ValidationResult
from app.processors import get_processor
from app.extractors import PatternExtractor
from app.validators import ValidationEngine


class ProcessingService:
    """Orchestrates document processing, extraction pipelines, and database persistence."""

    def __init__(self, db: Session):
        self.db = db
        self.extractor = PatternExtractor()
        self.validator = ValidationEngine(db)

    def execute_job(self, job_id: int) -> ProcessingJob:
        """Execute a processing job through its format-specific pipeline."""
        job = self.db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            raise ValueError(f"Processing job {job_id} not found.")

        start_time = time.time()
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()

        self._log(job.id, "INFO", "PROCESSING_STARTED", f"Execution started for pipeline '{job.processing_type}'.")
        self.db.commit()

        try:
            doc = job.document
            if not doc:
                raise ValueError("Associated document missing.")

            # 1. Format-specific processing
            processor = get_processor(job.processing_type or doc.file_type)
            result = processor.process(doc.storage_reference, job.extraction_configuration)
            self._log(job.id, "INFO", "CONTENT_EXTRACTED", f"Extracted content successfully using {result['metadata']['processor']}.")

            # 2. Extract configured fields
            records_to_create = []

            # If tabular records (CSV / Excel)
            if result.get("records"):
                for idx, row in enumerate(result["records"], start=1):
                    extracted_fields = self.extractor.extract_from_row(row)
                    record_data = {k: v["normalized_value"] for k, v in extracted_fields.items()}

                    # Run validation engine
                    val_outcomes = self.validator.validate_record(record_data)
                    rec_status = self.validator.compute_record_status(val_outcomes)

                    rec = ExtractedRecord(
                        processing_job_id=job.id,
                        record_number=idx,
                        extracted_data=record_data,
                        validation_status=rec_status,
                        confidence_score=0.95,
                        is_approved=False
                    )
                    self.db.add(rec)
                    self.db.flush()

                    # Save validation results
                    for v_res in val_outcomes:
                        vr = ValidationResult(
                            extracted_record_id=rec.id,
                            field_name=v_res["field_name"],
                            validation_rule=v_res["rule"],
                            status=v_res["status"],
                            message=v_res["message"]
                        )
                        self.db.add(vr)

                    for fname, fdata in extracted_fields.items():
                        field_val_status = ValidationStatus.VALID
                        # Check if any validation outcome failed for this field
                        matching_val = [v for v in val_outcomes if v["field_name"] == fname]
                        if matching_val:
                            worst_status = matching_val[0]["status"]
                            field_val_status = ValidationStatus(worst_status)

                        field = ExtractedField(
                            extracted_record_id=rec.id,
                            field_name=fname,
                            extracted_value=fdata["extracted_value"],
                            normalized_value=fdata["normalized_value"],
                            confidence_score=fdata["confidence"],
                            extraction_source=fdata["source"],
                            validation_status=field_val_status,
                            validation_message=matching_val[0]["message"] if matching_val else None
                        )
                        self.db.add(field)

            # If text/document-based (PDF / Image / OCR)
            else:
                raw_text = result.get("raw_text", "")
                extracted_fields = self.extractor.extract_from_text(raw_text, source=job.processing_type)
                record_data = {k: v["normalized_value"] for k, v in extracted_fields.items()}

                # Run validation engine
                val_outcomes = self.validator.validate_record(record_data)
                rec_status = self.validator.compute_record_status(val_outcomes)

                field_confs = [v["confidence"] for v in extracted_fields.values()]
                avg_conf = round(sum(field_confs) / len(field_confs), 2) if field_confs else 0.85

                rec = ExtractedRecord(
                    processing_job_id=job.id,
                    record_number=1,
                    extracted_data=record_data,
                    validation_status=rec_status,
                    confidence_score=avg_conf,
                    is_approved=False
                )
                self.db.add(rec)
                self.db.flush()

                # Save validation results
                for v_res in val_outcomes:
                    vr = ValidationResult(
                        extracted_record_id=rec.id,
                        field_name=v_res["field_name"],
                        validation_rule=v_res["rule"],
                        status=v_res["status"],
                        message=v_res["message"]
                    )
                    self.db.add(vr)

                for fname, fdata in extracted_fields.items():
                    field_val_status = ValidationStatus.VALID
                    matching_val = [v for v in val_outcomes if v["field_name"] == fname]
                    if matching_val:
                        worst_status = matching_val[0]["status"]
                        field_val_status = ValidationStatus(worst_status)

                    field = ExtractedField(
                        extracted_record_id=rec.id,
                        field_name=fname,
                        extracted_value=fdata["extracted_value"],
                        normalized_value=fdata["normalized_value"],
                        confidence_score=fdata["confidence"],
                        extraction_source=fdata["source"],
                        validation_status=field_val_status,
                        validation_message=matching_val[0]["message"] if matching_val else None
                    )
                    self.db.add(field)

            # Update job status
            job.status = JobStatus.NEEDS_REVIEW
            job.completed_at = datetime.utcnow()
            job.processing_duration = round(time.time() - start_time, 2)
            self._log(
                job.id,
                "INFO",
                "EXTRACTION_COMPLETED",
                f"Job completed in {job.processing_duration} seconds. Extracted records staged for review."
            )
            self.db.commit()
            self.db.refresh(job)
            return job

        except Exception as e:
            self.db.rollback()
            job.status = JobStatus.FAILED
            job.error_summary = str(e)
            job.completed_at = datetime.utcnow()
            job.processing_duration = round(time.time() - start_time, 2)
            self._log(job.id, "ERROR", "PROCESSING_FAILED", f"Job failed: {str(e)}")
            self.db.commit()
            self.db.refresh(job)
            return job

    def _log(self, job_id: int, level: str, event_type: str, message: str):
        """Append an event to the processing log."""
        log = ProcessingLog(
            processing_job_id=job_id,
            log_level=level,
            event_type=event_type,
            message=message
        )
        self.db.add(log)

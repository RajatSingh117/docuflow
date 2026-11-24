from datetime import datetime, timedelta, timezone
from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.services.processing_service import ProcessingService
from app.models.job import ProcessingJob, JobStatus, ProcessingLog
from app.models.schedule import ScheduledJob, ScheduledJobExecution
from app.models.document import Document


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document_task(self, job_id: int):
    """Celery background worker task for async document processing with retry handling."""
    db = SessionLocal()
    try:
        service = ProcessingService(db)
        job = service.execute_job(job_id)
        if job.status == JobStatus.FAILED:
            # If recoverable error, attempt retry
            raise RuntimeError(f"Processing failed: {job.error_summary}")
        return {"job_id": job.id, "status": job.status.value, "duration": job.processing_duration}
    except Exception as exc:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if job:
            job.retry_count = self.request.retries + 1
            db.commit()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise exc
    finally:
        db.close()


@celery_app.task
def run_scheduled_job_task(scheduled_job_id: int):
    """Executes a recurring scheduled processing job and records ScheduledJobExecution."""
    db = SessionLocal()
    try:
        sched = db.query(ScheduledJob).filter(ScheduledJob.id == scheduled_job_id).first()
        if not sched or not sched.is_active:
            return {"status": "skipped", "reason": "Inactive or missing schedule"}

        # Find latest pending or unprocessed document
        config = sched.schedule_configuration or {}
        target_type = config.get("file_type")

        doc_query = db.query(Document)
        if target_type:
            doc_query = doc_query.filter(Document.file_type == target_type)
        doc = doc_query.order_by(Document.uploaded_at.desc()).first()

        if not doc:
            return {"status": "skipped", "reason": "No matching document for schedule"}

        # Create traceable processing job
        proc_job = ProcessingJob(
            document_id=doc.id,
            created_by=sched.created_by,
            processing_type="auto",
            status=JobStatus.QUEUED
        )
        db.add(proc_job)
        db.flush()

        # Record ScheduledJobExecution
        execution = ScheduledJobExecution(
            scheduled_job_id=sched.id,
            processing_job_id=proc_job.id,
            execution_status="PROCESSING",
            started_at=datetime.now(timezone.utc)
        )
        db.add(execution)
        db.commit()

        # Execute processing
        service = ProcessingService(db)
        completed_job = service.execute_job(proc_job.id)

        execution.execution_status = "SUCCESS" if completed_job.status != JobStatus.FAILED else "FAILED"
        execution.completed_at = datetime.now(timezone.utc)
        execution.error_summary = completed_job.error_summary

        # Update next run timestamp based on frequency
        now = datetime.now(timezone.utc)
        if sched.schedule_type == "daily":
            sched.next_run_at = now + timedelta(days=1)
        elif sched.schedule_type == "weekly":
            sched.next_run_at = now + timedelta(weeks=1)
        elif sched.schedule_type == "monthly":
            sched.next_run_at = now + timedelta(days=30)

        db.commit()
        return {"schedule_id": sched.id, "job_id": completed_job.id, "status": execution.execution_status}
    finally:
        db.close()

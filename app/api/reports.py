from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.report import GeneratedReport
from app.models.job import ProcessingJob, JobStatus
from app.models.user import User
from app.models.audit import AuditLog
from app.api.deps import require_manager_or_admin, require_any_authenticated
from app.report_generators import ExcelReportGenerator, PDFReportGenerator

router = APIRouter(prefix="/api/reports", tags=["Reports"])


class GenerateReportRequest(BaseModel):
    job_id: int
    report_type: str  # "excel" or "pdf"


@router.get("")
def list_reports(
    job_id: Optional[int] = Query(None),
    report_type: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db)
):
    """Retrieve list of generated Excel and PDF reports."""
    query = db.query(GeneratedReport)
    if job_id:
        query = query.filter(GeneratedReport.processing_job_id == job_id)
    if report_type:
        query = query.filter(GeneratedReport.report_type == report_type.lower())

    reports = query.order_by(GeneratedReport.created_at.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": r.id,
            "processing_job_id": r.processing_job_id,
            "document_name": r.job.document.original_filename if r.job and r.job.document else "Unknown",
            "report_type": r.report_type,
            "filename": r.filename,
            "generated_by": r.generator.name if r.generator else "System",
            "created_at": r.created_at.isoformat()
        }
        for r in reports
    ]


@router.post("/generate", status_code=status.HTTP_201_CREATED)
def generate_report(
    req: GenerateReportRequest,
    request: Request,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Generate structured Excel or PDF report from approved job records."""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == req.job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processing job not found.")

    rtype = req.report_type.lower()
    if rtype not in ["excel", "pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported report type. Supported types: 'excel' or 'pdf'."
        )

    if rtype == "excel":
        generator = ExcelReportGenerator()
        file_path_str = generator.generate(job, current_user.name)
    else:
        generator = PDFReportGenerator()
        file_path_str = generator.generate(job, current_user.name)

    filename = Path(file_path_str).name

    # Save to GeneratedReport database table
    rep = GeneratedReport(
        processing_job_id=job.id,
        report_type=rtype,
        filename=filename,
        storage_reference=file_path_str,
        generated_by=current_user.id
    )
    db.add(rep)
    db.flush()

    # Audit log
    client_ip = request.client.host if request.client else "127.0.0.1"
    audit = AuditLog(
        user_id=current_user.id,
        action="REPORT_GENERATED",
        entity_type="GeneratedReport",
        entity_id=rep.id,
        new_values={"job_id": job.id, "type": rtype, "filename": filename},
        ip_address=client_ip
    )
    db.add(audit)
    db.commit()
    db.refresh(rep)

    return {
        "id": rep.id,
        "job_id": job.id,
        "report_type": rep.report_type,
        "filename": rep.filename,
        "download_url": f"/api/reports/{rep.id}/download"
    }


@router.get("/{report_id}/download")
def download_report(
    report_id: int,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db)
):
    """Securely download generated report file with strict path traversal checks."""
    rep = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not rep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report record not found.")

    file_path = Path(rep.storage_reference).resolve()
    # Path traversal validation
    storage_root = Path("./storage").resolve()
    if not str(file_path).startswith(str(storage_root)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path traversal detected.")

    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file missing on server disk.")

    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if rep.report_type == "excel" else "application/pdf"

    return FileResponse(
        path=str(file_path),
        filename=rep.filename,
        media_type=media_type
    )

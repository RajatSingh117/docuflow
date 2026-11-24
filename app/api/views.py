from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.models.document import Document
from app.models.job import ProcessingJob, JobStatus
from app.api.deps import get_current_user_optional
from app.services.analytics_service import get_dashboard_metrics

router = APIRouter(tags=["Frontend Views"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, current_user: User = Depends(get_current_user_optional)):
    """Render the sign-in page."""
    if current_user:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Render the main executive dashboard."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    metrics = get_dashboard_metrics(db)
    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "dashboard",
            "metrics": metrics,
            "current_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        }
    )


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Admin-only user management view."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    if current_user.role != UserRole.ADMIN:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    users = db.query(User).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "users",
            "users": users
        }
    )


@router.get("/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional)
):
    """Render system settings page."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    db_backend = "PostgreSQL" if "postgresql" in settings.DATABASE_URL else "SQLite (Local Development / Testing)"
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "settings",
            "app_settings": settings,
            "db_backend": db_backend
        }
    )


@router.get("/logs", response_class=HTMLResponse)
def logs_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Render activity and audit logs page."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    return templates.TemplateResponse(
        "logs/index.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "logs",
            "logs": logs
        }
    )


@router.get("/documents", response_class=HTMLResponse)
def documents_page(
    request: Request,
    search: str = None,
    file_type: str = None,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Render documents catalog page."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    query = db.query(Document)
    if search:
        query = query.filter(Document.original_filename.ilike(f"%{search}%"))
    if file_type:
        query = query.filter(Document.file_type == file_type.lower())

    docs = query.order_by(Document.uploaded_at.desc()).all()
    return templates.TemplateResponse(
        "documents/index.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "documents",
            "documents": docs,
            "search": search,
            "file_type": file_type
        }
    )


@router.get("/documents/upload", response_class=HTMLResponse)
def upload_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional)
):
    """Render document upload interface."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    if current_user.role == UserRole.VIEWER:
        return RedirectResponse(url="/documents", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        "documents/upload.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "upload"
        }
    )


@router.get("/documents/{document_id}", response_class=HTMLResponse)
def document_detail_page(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Render document details view."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return RedirectResponse(url="/documents", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        "documents/detail.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "documents",
            "document": doc
        }
    )


@router.get("/processing/jobs", response_class=HTMLResponse)
def processing_jobs_page(
    request: Request,
    status: str = None,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Render processing jobs list view."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    query = db.query(ProcessingJob)
    if status:
        query = query.filter(ProcessingJob.status == status)

    jobs = query.order_by(ProcessingJob.created_at.desc()).all()
    return templates.TemplateResponse(
        "processing/jobs.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "jobs",
            "jobs": jobs,
            "current_status": status
        }
    )


@router.get("/processing/jobs/{job_id}", response_class=HTMLResponse)
def processing_job_detail_page(
    job_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Render processing job detail view."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        return RedirectResponse(url="/processing/jobs", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        "processing/detail.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "jobs",
            "job": job
        }
    )


@router.get("/processing/review", response_class=HTMLResponse)
def review_list_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Render list of jobs awaiting review."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    jobs = db.query(ProcessingJob).filter(ProcessingJob.status == JobStatus.NEEDS_REVIEW).order_by(ProcessingJob.created_at.desc()).all()
    return templates.TemplateResponse(
        "review/index.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "review",
            "jobs": jobs
        }
    )


@router.get("/processing/review/{job_id}", response_class=HTMLResponse)
def review_detail_page(
    job_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Render review and approval interface for a specific job."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        return RedirectResponse(url="/processing/review", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        "review/detail.html",
        {
            "request": request,
            "current_user": current_user,
            "active_page": "review",
            "job": job
        }
    )

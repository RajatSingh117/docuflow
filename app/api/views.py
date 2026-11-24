from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models.user import User, UserRole
from app.models.audit import AuditLog
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

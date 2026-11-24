from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import require_any_authenticated
from app.models.user import User
from app.services.analytics_service import get_dashboard_metrics

router = APIRouter(prefix="/api/analytics", tags=["Analytics & KPIs"])


@router.get("/dashboard")
def get_dashboard_data(
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db)
):
    """Retrieve real-time dashboard analytics from actual database records."""
    metrics = get_dashboard_metrics(db)
    # Serialize documents and jobs for JSON response
    recent_docs_serialized = [
        {
            "id": d.id,
            "filename": d.original_filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "uploaded_by": d.uploader.name if d.uploader else "System",
            "uploaded_at": d.uploaded_at.isoformat(),
            "status": d.upload_status.value
        }
        for d in metrics["recent_documents"]
    ]

    recent_jobs_serialized = [
        {
            "id": j.id,
            "document_name": j.document.original_filename if j.document else "Unknown",
            "processing_type": j.processing_type,
            "status": j.status.value,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            "duration": j.processing_duration
        }
        for j in metrics["recent_jobs"]
    ]

    metrics_copy = metrics.copy()
    metrics_copy["recent_documents"] = recent_docs_serialized
    metrics_copy["recent_jobs"] = recent_jobs_serialized
    return metrics_copy

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schedule import ScheduledJob, ScheduledJobExecution
from app.models.user import User
from app.models.audit import AuditLog
from app.api.deps import require_manager_or_admin, require_any_authenticated
from app.tasks.processing_tasks import run_scheduled_job_task

router = APIRouter(prefix="/api/schedules", tags=["Scheduled Automation"])


class ScheduleCreateRequest(BaseModel):
    name: str
    schedule_type: str  # "daily", "weekly", "monthly"
    file_type: Optional[str] = "all"
    start_delay_hours: Optional[int] = 24


@router.get("")
def list_schedules(
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db)
):
    """List recurring scheduled processing jobs and their execution histories."""
    scheds = db.query(ScheduledJob).order_by(ScheduledJob.created_at.desc()).all()
    results = []
    for s in scheds:
        last_exec = (
            db.query(ScheduledJobExecution)
            .filter(ScheduledJobExecution.scheduled_job_id == s.id)
            .order_by(ScheduledJobExecution.started_at.desc())
            .first()
        )
        results.append({
            "id": s.id,
            "name": s.name,
            "schedule_type": s.schedule_type,
            "is_active": s.is_active,
            "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
            "created_by": s.creator.name if s.creator else "System",
            "created_at": s.created_at.isoformat(),
            "last_execution": {
                "status": last_exec.execution_status,
                "started_at": last_exec.started_at.isoformat(),
                "error_summary": last_exec.error_summary
            } if last_exec else None
        })
    return results


@router.post("", status_code=status.HTTP_201_CREATED)
def create_schedule(
    req: ScheduleCreateRequest,
    request: Request,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Create a new recurring scheduled processing automation."""
    stype = req.schedule_type.lower()
    if stype not in ["daily", "weekly", "monthly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule type must be 'daily', 'weekly', or 'monthly'."
        )

    now = datetime.now(timezone.utc)
    if stype == "daily":
        next_run = now + timedelta(days=1)
    elif stype == "weekly":
        next_run = now + timedelta(weeks=1)
    else:
        next_run = now + timedelta(days=30)

    sched = ScheduledJob(
        name=req.name,
        created_by=current_user.id,
        schedule_type=stype,
        schedule_configuration={"file_type": req.file_type if req.file_type != "all" else None},
        is_active=True,
        next_run_at=next_run
    )
    db.add(sched)
    db.flush()

    audit = AuditLog(
        user_id=current_user.id,
        action="SCHEDULE_CREATED",
        entity_type="ScheduledJob",
        entity_id=sched.id,
        new_values={"name": sched.name, "type": sched.schedule_type}
    )
    db.add(audit)
    db.commit()
    db.refresh(sched)

    return {
        "id": sched.id,
        "name": sched.name,
        "schedule_type": sched.schedule_type,
        "is_active": sched.is_active,
        "next_run_at": sched.next_run_at.isoformat()
    }


@router.put("/{schedule_id}/toggle")
def toggle_schedule(
    schedule_id: int,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Pause or resume a scheduled job."""
    sched = db.query(ScheduledJob).filter(ScheduledJob.id == schedule_id).first()
    if not sched:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found.")

    sched.is_active = not sched.is_active
    audit = AuditLog(
        user_id=current_user.id,
        action="SCHEDULE_TOGGLED",
        entity_type="ScheduledJob",
        entity_id=sched.id,
        new_values={"is_active": sched.is_active}
    )
    db.add(audit)
    db.commit()
    return {"id": sched.id, "is_active": sched.is_active}


@router.post("/{schedule_id}/run")
def trigger_schedule_now(
    schedule_id: int,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Manually trigger immediate execution of a scheduled job."""
    sched = db.query(ScheduledJob).filter(ScheduledJob.id == schedule_id).first()
    if not sched:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found.")

    result = run_scheduled_job_task(sched.id)
    return result


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Delete a scheduled automation job."""
    sched = db.query(ScheduledJob).filter(ScheduledJob.id == schedule_id).first()
    if not sched:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found.")

    db.delete(sched)
    db.commit()
    return {"message": f"Schedule '{sched.name}' deleted successfully."}

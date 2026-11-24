from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas.user import UserResponse, UserUpdate
from app.api.deps import require_admin
from app.services.auth_service import hash_password

router = APIRouter(prefix="/api/users", tags=["User Management"])


@router.get("", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 50,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-only: list all users."""
    users = db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-only: get specific user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-only: update user information (role, active status, name)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    old_values = {"name": user.name, "role": user.role.value, "is_active": user.is_active}

    if user_in.name is not None:
        user.name = user_in.name
    if user_in.role is not None:
        user.role = user_in.role
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
    if user_in.password:
        user.password_hash = hash_password(user_in.password)

    new_values = {"name": user.name, "role": user.role.value, "is_active": user.is_active}

    audit = AuditLog(
        user_id=current_admin.id,
        action="USER_UPDATED",
        entity_type="User",
        entity_id=user.id,
        old_values=old_values,
        new_values=new_values
    )
    db.add(audit)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-only: deactivate or delete user."""
    if user_id == current_admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own admin account.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.is_active = False
    audit = AuditLog(
        user_id=current_admin.id,
        action="USER_DEACTIVATED",
        entity_type="User",
        entity_id=user.id,
        new_values={"is_active": False}
    )
    db.add(audit)
    db.commit()
    return {"message": f"User {user.email} deactivated successfully."}

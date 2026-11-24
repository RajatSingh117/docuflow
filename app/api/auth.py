from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.schemas.user import UserLogin, UserCreate, UserResponse, Token
from app.services.auth_service import verify_password, hash_password, create_access_token
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(login_data: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    """Authenticate user with email and password, return JWT token and set session cookie."""
    user = db.query(User).filter(User.email == login_data.email.lower()).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact an administrator.",
        )

    # Update last login timestamp
    user.last_login = datetime.utcnow()

    # Record login audit log
    client_ip = request.client.host if request.client else "unknown"
    audit = AuditLog(
        user_id=user.id,
        action="USER_LOGIN",
        entity_type="User",
        entity_id=user.id,
        new_values={"email": user.email, "role": user.role.value},
        ip_address=client_ip
    )
    db.add(audit)
    db.commit()
    db.refresh(user)

    # Create token
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})

    # Set HTTP-only cookie for secure browser navigation
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=86400,
        samesite="lax",
        secure=False  # Set True in production with HTTPS
    )

    return Token(access_token=access_token, token_type="bearer", user=UserResponse.model_validate(user))


@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Log out current user and clear session cookie."""
    audit = AuditLog(
        user_id=current_user.id,
        action="USER_LOGOUT",
        entity_type="User",
        entity_id=current_user.id,
        new_values={"email": current_user.email}
    )
    db.add(audit)
    db.commit()

    response.delete_cookie(key="access_token")
    return {"message": "Successfully logged out."}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return profile details of the authenticated user."""
    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: UserCreate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin-only endpoint to create a new user account (PRD Section 3.1)."""
    existing = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    new_user = User(
        name=user_in.name,
        email=user_in.email.lower(),
        password_hash=hash_password(user_in.password),
        role=user_in.role,
        is_active=user_in.is_active
    )
    db.add(new_user)
    db.flush()

    audit = AuditLog(
        user_id=current_admin.id,
        action="USER_CREATED",
        entity_type="User",
        entity_id=new_user.id,
        new_values={"name": new_user.name, "email": new_user.email, "role": new_user.role.value}
    )
    db.add(audit)
    db.commit()
    db.refresh(new_user)
    return new_user

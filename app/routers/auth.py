"""Authentication and profile routes.

Improvements applied:
- IDEA-15: AccountLockedError is surfaced as 423 Locked
- IDEA-12: /profile, /password, /account endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import security_manager
from app.dependencies import get_current_user, get_db
from app.models.conversion import Conversion
from app.models.user import User
from app.schemas.user import (
    PasswordChange,
    ProfileOut,
    Token,
    UserCreate,
    UserLogin,
    UserOut,
)
from app.services.auth_service import AccountLockedError, AuthError, auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _make_token(user: User) -> Token:
    access_token = security_manager.create_access_token(subject=user.id)
    return Token(access_token=access_token, user=UserOut.model_validate(user))


# ── Registration & Login ──────────────────────────────────────────────────────

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)) -> Token:
    try:
        user = auth_service.register(db, data)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return _make_token(user)


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)) -> Token:
    try:
        user = auth_service.authenticate(db, data.email, data.password)
    except AccountLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="البريد الإلكتروني أو كلمة المرور غير صحيحة.",
        )
    return _make_token(user)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


# ── Profile — IDEA-12 ─────────────────────────────────────────────────────────

@router.get("/profile", response_model=ProfileOut)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileOut:
    """Return the current user's profile with usage statistics."""
    total = db.query(Conversion).filter(Conversion.user_id == current_user.id).count()
    return ProfileOut(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at,
        total_conversions=total,
        monthly_chars_used=current_user.monthly_chars_used or 0,
    )


@router.patch("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Change the current user's password."""
    try:
        auth_service.change_password(db, current_user, data.current_password, data.new_password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Permanently delete the current user's account and all data."""
    auth_service.delete_account(db, current_user)

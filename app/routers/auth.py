"""Authentication and profile routes.

Improvements applied:
- IDEA-15: AccountLockedError is surfaced as 423 Locked
- IDEA-12: /profile, /password, /account endpoints
- IDEA-14: Refresh tokens issued as HttpOnly cookies; /refresh and /logout added
"""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
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

_REFRESH_COOKIE = "vf_refresh"
_COOKIE_OPTS = dict(httponly=True, samesite="lax", secure=False)   # set secure=True behind HTTPS


def _set_refresh_cookie(response: Response, user: User) -> None:
    token = security_manager.create_refresh_token(subject=user.id)
    max_age = security_manager.refresh_days * 86_400
    response.set_cookie(
        key=_REFRESH_COOKIE, value=token,
        max_age=max_age, path="/api/auth",
        **_COOKIE_OPTS,
    )


def _make_token(user: User) -> Token:
    access_token = security_manager.create_access_token(subject=user.id)
    return Token(access_token=access_token, user=UserOut.model_validate(user))


# ── Registration & Login ──────────────────────────────────────────────────────

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, response: Response, db: Session = Depends(get_db)) -> Token:
    try:
        user = auth_service.register(db, data)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    _set_refresh_cookie(response, user)
    return _make_token(user)


@router.post("/login", response_model=Token)
def login(data: UserLogin, response: Response, db: Session = Depends(get_db)) -> Token:
    try:
        user = auth_service.authenticate(db, data.email, data.password)
    except AccountLockedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="البريد الإلكتروني أو كلمة المرور غير صحيحة.",
        )
    _set_refresh_cookie(response, user)
    return _make_token(user)


# ── Refresh & Logout — IDEA-14 ────────────────────────────────────────────────

@router.post("/refresh", response_model=Token)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    vf_refresh: str | None = Cookie(default=None),
) -> Token:
    """Issue a new access token using the refresh cookie."""
    if not vf_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="انتهت الجلسة.")
    user_id = security_manager.decode_refresh_token(vf_refresh)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="رمز التحديث غير صالح.")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="المستخدم غير موجود.")
    _set_refresh_cookie(response, user)   # rotate the cookie
    return _make_token(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    """Clear the refresh cookie."""
    response.delete_cookie(key=_REFRESH_COOKIE, path="/api/auth", **_COOKIE_OPTS)


# ── /me ───────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


# ── Profile — IDEA-12 ─────────────────────────────────────────────────────────

@router.get("/profile", response_model=ProfileOut)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileOut:
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
    try:
        auth_service.change_password(db, current_user, data.current_password, data.new_password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    auth_service.delete_account(db, current_user)
    response.delete_cookie(key=_REFRESH_COOKIE, path="/api/auth", **_COOKIE_OPTS)

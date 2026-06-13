"""Authentication service: registration, login, account management.

Improvements applied:
- IDEA-15: Account lockout after 5 consecutive failed logins (15-minute lock)
- IDEA-12: change_password and delete_account methods
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import SecurityManager, security_manager
from app.models.user import User
from app.schemas.user import UserCreate

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class AuthError(Exception):
    """Raised for authentication / registration problems (safe message)."""


class AccountLockedError(AuthError):
    """Raised when an account is temporarily locked."""

    def __init__(self, until: datetime) -> None:
        self.until = until
        # Format time remaining
        remaining = max(0, int((until - datetime.now(timezone.utc)).total_seconds() / 60))
        super().__init__(
            f"الحساب مقفل مؤقتاً بسبب محاولات تسجيل دخول متكررة. "
            f"حاول مرة أخرى بعد {remaining} دقيقة."
        )


class AuthService:
    """Handles account creation, login, and management against the database."""

    def __init__(self, security: SecurityManager = security_manager) -> None:
        self.security = security

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, db: Session, data: UserCreate) -> User:
        """Create a new user, enforcing unique email and username."""
        if db.query(User).filter(User.email == data.email).first():
            raise AuthError("يوجد حساب مسجّل بهذا البريد الإلكتروني مسبقاً.")
        if db.query(User).filter(User.username == data.username).first():
            raise AuthError("اسم المستخدم هذا محجوز. الرجاء اختيار اسم آخر.")

        user = User(
            username=data.username,
            email=data.email,
            hashed_password=self.security.hash_password(data.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # ── Authentication with lockout — IDEA-15 ────────────────────────────────

    def authenticate(
        self, db: Session, email: str, password: str
    ) -> Optional[User]:
        """Return the user if credentials are valid.

        Raises AccountLockedError if the account is locked.
        Returns None if credentials are wrong.
        """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None

        # Check lockout
        now = datetime.now(timezone.utc)
        lockout = user.lockout_until
        if lockout is not None:
            if lockout.tzinfo is None:
                lockout = lockout.replace(tzinfo=timezone.utc)
            if lockout > now:
                raise AccountLockedError(lockout)
            # Lockout expired — clear it
            user.lockout_until = None
            user.failed_login_attempts = 0
            db.commit()

        # Verify password
        if not self.security.verify_password(password, user.hashed_password):
            attempts = (user.failed_login_attempts or 0) + 1
            if attempts >= MAX_FAILED_ATTEMPTS:
                user.lockout_until = now + timedelta(minutes=LOCKOUT_MINUTES)
                user.failed_login_attempts = 0
                db.commit()
                raise AccountLockedError(user.lockout_until)
            user.failed_login_attempts = attempts
            db.commit()
            return None

        # Successful login — reset counters
        if user.failed_login_attempts or user.lockout_until:
            user.failed_login_attempts = 0
            user.lockout_until = None
            db.commit()

        return user

    # ── Profile management — IDEA-12 ─────────────────────────────────────────

    def change_password(
        self, db: Session, user: User, current_password: str, new_password: str
    ) -> None:
        """Change the user's password after verifying the current one."""
        if not self.security.verify_password(current_password, user.hashed_password):
            raise AuthError("كلمة المرور الحالية غير صحيحة.")
        user.hashed_password = self.security.hash_password(new_password)
        db.commit()

    def delete_account(self, db: Session, user: User) -> None:
        """Permanently delete the user and all associated data."""
        db.delete(user)
        db.commit()


# Shared instance.
auth_service = AuthService()

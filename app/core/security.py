"""Password hashing and JWT helpers — IDEA-14: refresh tokens added.

Access tokens:  short-lived (15 min), sent in response body / Authorization header.
Refresh tokens: long-lived (7 days),  stored in HttpOnly SameSite cookie.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import jwt

from app.config import settings


class SecurityManager:
    """Stateless helper for hashing passwords and issuing/verifying JWTs."""

    def __init__(
        self,
        secret_key: str = settings.secret_key,
        algorithm: str = settings.algorithm,
        expire_minutes: int = settings.access_token_expire_minutes,
        refresh_days: int = settings.refresh_token_expire_days,
    ) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes
        self.refresh_days = refresh_days

    # ── Password hashing ──────────────────────────────────────────────────────

    @staticmethod
    def _to_bytes(password: str) -> bytes:
        return password.encode("utf-8")[:72]

    def hash_password(self, password: str) -> str:
        hashed = bcrypt.hashpw(self._to_bytes(password), bcrypt.gensalt())
        return hashed.decode("utf-8")

    def verify_password(self, password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(
                self._to_bytes(password), hashed_password.encode("utf-8")
            )
        except (ValueError, TypeError):
            return False

    # ── JWT helpers ───────────────────────────────────────────────────────────

    def _encode(self, payload: dict[str, Any]) -> str:
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def _decode_raw(self, token: str) -> dict[str, Any]:
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

    # ── Access token ──────────────────────────────────────────────────────────

    def create_access_token(
        self, subject: str | int, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a signed access JWT.  type='access' guards against using a
        refresh token in the Authorization header."""
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=self.expire_minutes)
        )
        return self._encode({"sub": str(subject), "exp": expire, "type": "access"})

    def decode_token(self, token: str) -> Optional[str]:
        """Return the user id (sub) from a valid *access* token, else None."""
        try:
            payload = self._decode_raw(token)
            if payload.get("type") != "access":
                return None
            return payload.get("sub")
        except jwt.PyJWTError:
            return None

    # ── Refresh token — IDEA-14 ───────────────────────────────────────────────

    def create_refresh_token(self, subject: str | int) -> str:
        """Create a long-lived refresh JWT (7 days)."""
        expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_days)
        return self._encode({"sub": str(subject), "exp": expire, "type": "refresh"})

    def decode_refresh_token(self, token: str) -> Optional[str]:
        """Return the user id from a valid refresh token, else None."""
        try:
            payload = self._decode_raw(token)
            if payload.get("type") != "refresh":
                return None
            return payload.get("sub")
        except jwt.PyJWTError:
            return None


# Shared instance for convenience.
security_manager = SecurityManager()

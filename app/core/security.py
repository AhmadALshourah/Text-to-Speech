"""Password hashing and JWT helpers.

Uses `bcrypt` directly for password hashing and `PyJWT` for tokens, both of
which are well-supported on modern Python versions.
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
    ) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    # --- Password hashing -------------------------------------------------
    @staticmethod
    def _to_bytes(password: str) -> bytes:
        """Encode and truncate to bcrypt's 72-byte limit."""
        return password.encode("utf-8")[:72]

    def hash_password(self, password: str) -> str:
        """Return a bcrypt hash for the given plaintext password."""
        hashed = bcrypt.hashpw(self._to_bytes(password), bcrypt.gensalt())
        return hashed.decode("utf-8")

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Check a plaintext password against a stored bcrypt hash."""
        try:
            return bcrypt.checkpw(
                self._to_bytes(password), hashed_password.encode("utf-8")
            )
        except (ValueError, TypeError):
            return False

    # --- JWT --------------------------------------------------------------
    def create_access_token(
        self, subject: str | int, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a signed JWT whose `sub` claim is the user id."""
        expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=self.expire_minutes)
        )
        to_encode: dict[str, Any] = {"sub": str(subject), "exp": expire}
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Optional[str]:
        """Return the `sub` (user id) from a valid token, or None if invalid."""
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )
            return payload.get("sub")
        except jwt.PyJWTError:
            return None


# Shared instance for convenience.
security_manager = SecurityManager()

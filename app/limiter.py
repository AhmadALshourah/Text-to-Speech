"""Shared rate-limiter instance — IDEA-13.

Using per-user key when an Authorization header is present, falling back to IP.
"""

from fastapi import Request
from slowapi import Limiter


def _user_or_ip_key(request: Request) -> str:
    """Rate-limit per user-id when authenticated, else per IP."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.removeprefix("Bearer ").strip()
        if token:
            try:
                from app.core.security import security_manager
                uid = security_manager.decode_token(token)
                if uid:
                    return f"user:{uid}"
            except Exception:
                pass
    host = getattr(request.client, "host", "unknown")
    return f"ip:{host}"


limiter = Limiter(key_func=_user_or_ip_key)

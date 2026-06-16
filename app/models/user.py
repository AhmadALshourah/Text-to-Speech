"""User ORM model."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """A registered application user."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Account lockout — IDEA-15
    failed_login_attempts = Column(Integer, default=0, server_default="0", nullable=False)
    lockout_until = Column(DateTime(timezone=True), nullable=True)

    # Monthly usage quota — IDEA-34
    monthly_chars_used = Column(Integer, default=0, server_default="0", nullable=False)
    monthly_chars_reset = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    conversions = relationship(
        "Conversion", back_populates="user", cascade="all, delete-orphan"
    )
    shares = relationship(
        "Share", back_populates="user", cascade="all, delete-orphan",
        foreign_keys="Share.user_id",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} username={self.username!r}>"

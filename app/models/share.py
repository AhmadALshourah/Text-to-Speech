"""Share ORM model — IDEA-10."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import relationship

from app.database import Base


class Share(Base):
    """A time-limited public share of a synthesised audio clip."""

    __tablename__ = "shares"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    uuid         = Column(String(36), unique=True, nullable=False, index=True)
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    text_preview = Column(String(200), nullable=True)
    voice        = Column(String(100), nullable=False)
    audio_data   = Column(LargeBinary, nullable=False)
    created_at   = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at   = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="shares")

    def is_expired(self) -> bool:
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp < datetime.now(timezone.utc)

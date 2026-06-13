"""Conversion history ORM model — IDEA-06."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Conversion(Base):
    """One TTS synthesis request recorded in history."""

    __tablename__ = "conversions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text_preview = Column(String(200))   # first 200 chars of input text
    text_length = Column(Integer, nullable=False)
    voice = Column(String(100), nullable=False)
    rate = Column(String(10), nullable=False)
    volume = Column(String(10), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="conversions")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Conversion id={self.id} user_id={self.user_id} chars={self.text_length}>"

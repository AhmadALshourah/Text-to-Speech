"""Schemas for conversion history — IDEA-06."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConversionOut(BaseModel):
    """A single conversion history entry."""

    id: int
    text_preview: str | None
    text_length: int
    voice: str
    rate: str
    volume: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HistoryPage(BaseModel):
    """Paginated history response."""

    items: list[ConversionOut]
    total: int
    page: int
    pages: int
    per_page: int

"""Pydantic schemas for the share feature — IDEA-10."""

from datetime import datetime

from pydantic import BaseModel, Field


class ShareCreate(BaseModel):
    """Parameters used to create a shareable audio link."""

    text:   str       = Field(..., min_length=1, max_length=5000)
    voice:  str       = Field(default="en-US-GuyNeural")
    rate:   str       = Field(default="+0%")
    volume: str       = Field(default="+0%")
    ssml:   bool      = Field(default=False)


class ShareOut(BaseModel):
    """Response returned after creating a share."""

    uuid:         str
    url:          str
    expires_at:   datetime
    text_preview: str | None
    voice:        str

"""Pydantic schemas for text-to-speech requests and voices."""

import re

from pydantic import BaseModel, Field, field_validator

_SIGNED_PCT_RE = re.compile(r"^[+-]\d{1,3}%$")


class TTSRequest(BaseModel):
    """Payload for synthesizing speech from text."""

    text: str = Field(min_length=1, max_length=5000)
    voice: str = Field(default="en-US-GuyNeural")
    rate: str = Field(default="+0%")
    volume: str = Field(default="+0%")
    ssml: bool = Field(default=False)  # IDEA-25: skip preprocessing when True

    @field_validator("rate", "volume")
    @classmethod
    def _validate_signed_pct(cls, v: str) -> str:
        if not _SIGNED_PCT_RE.match(v):
            raise ValueError("must be a signed percentage string like '+10%' or '-5%'")
        return v


class PreviewRequest(BaseModel):
    """Payload for a quick voice preview — IDEA-07."""

    voice: str = Field(default="en-US-GuyNeural")
    text: str = Field(default="", max_length=200)


class VoiceOut(BaseModel):
    """A single available voice."""

    id: str
    name: str
    locale: str
    gender: str

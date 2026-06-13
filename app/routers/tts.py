"""Text-to-speech routes.

Improvements applied:
- IDEA-07  : /preview endpoint for quick voice samples
- IDEA-13  : Rate limiting (10 synth/min per user)
- IDEA-06  : Conversion history is recorded after each synthesis
- IDEA-34  : Monthly character quota (500 000 chars/month)
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.dependencies import get_current_user, get_db
from app.limiter import limiter
from app.models.conversion import Conversion
from app.models.user import User
from app.schemas.tts import PreviewRequest, TTSRequest, VoiceOut
from app.services.tts_service import TTSError, tts_service

router = APIRouter(prefix="/api/tts", tags=["tts"])

MONTHLY_CHAR_LIMIT = 500_000


# ── Helpers ───────────────────────────────────────────────────────────────────

def _record_conversion(db: Session, user: User, text: str, voice: str, rate: str, volume: str) -> None:
    """Persist one history entry and update the monthly quota."""
    n = len(text)
    now = datetime.now(timezone.utc)

    # Reset monthly counter when the month changes — IDEA-34
    reset = user.monthly_chars_reset
    if reset is not None and reset.tzinfo is None:
        reset = reset.replace(tzinfo=timezone.utc)

    if reset is None or reset.month != now.month or reset.year != now.year:
        user.monthly_chars_used = 0
        user.monthly_chars_reset = now

    user.monthly_chars_used = (user.monthly_chars_used or 0) + n

    # History entry — IDEA-06
    conversion = Conversion(
        user_id=user.id,
        text_preview=text[:200],
        text_length=n,
        voice=voice,
        rate=rate,
        volume=volume,
    )
    db.add(conversion)
    db.commit()


def _check_quota(db: Session, user: User, text_len: int) -> None:
    """Raise 429 if the user has exceeded their monthly char limit — IDEA-34."""
    now = datetime.now(timezone.utc)
    reset = user.monthly_chars_reset
    if reset is not None and reset.tzinfo is None:
        reset = reset.replace(tzinfo=timezone.utc)

    used = user.monthly_chars_used or 0
    if reset is None or reset.month != now.month or reset.year != now.year:
        used = 0  # new month

    if used + text_len > MONTHLY_CHAR_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"تجاوزت الحد الشهري ({MONTHLY_CHAR_LIMIT:,} حرف). "
                f"المستخدم حتى الآن: {used:,} حرف. يتجدد الحد في أول الشهر القادم."
            ),
        )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/voices", response_model=list[VoiceOut])
def voices() -> list[VoiceOut]:
    """List available voices. Public — no auth required."""
    return tts_service.list_voices()


@router.post("/synthesize")
@limiter.limit("10/minute")
async def synthesize(
    request: Request,
    data: TTSRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Convert text to speech and return the MP3.

    Rate-limited to 10 requests/minute per user.
    Audio file is deleted from disk after streaming (BackgroundTask).
    """
    _check_quota(db, current_user, len(data.text))

    try:
        filepath = await tts_service.synthesize(
            text=data.text,
            voice=data.voice,
            rate=data.rate,
            volume=data.volume,
            ssml=data.ssml,
        )
    except TTSError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    # Record history + update quota (runs before the file is deleted)
    _record_conversion(db, current_user, data.text, data.voice, data.rate, data.volume)

    return FileResponse(
        path=filepath,
        media_type="audio/mpeg",
        filename="speech.mp3",
        background=BackgroundTask(filepath.unlink, missing_ok=True),
    )


@router.post("/preview")
@limiter.limit("20/minute")
async def preview(
    request: Request,
    data: PreviewRequest,
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Return a short audio sample for voice selection — IDEA-07."""
    try:
        filepath = await tts_service.preview(voice=data.voice, user_text=data.text)
    except TTSError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return FileResponse(
        path=filepath,
        media_type="audio/mpeg",
        filename="preview.mp3",
        background=BackgroundTask(filepath.unlink, missing_ok=True),
    )

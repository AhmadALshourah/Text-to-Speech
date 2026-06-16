"""Text-to-speech routes.

Improvements applied:
- IDEA-02  : In-memory TTL cache for synthesis results
- IDEA-07  : /preview endpoint for quick voice samples
- IDEA-13  : Rate limiting (10 synth/min per user)
- IDEA-06  : Conversion history recorded after each synthesis
- IDEA-34  : Monthly character quota (500 000 chars/month)
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app import cache as audio_cache
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
    n = len(text)
    now = datetime.now(timezone.utc)

    reset = user.monthly_chars_reset
    if reset is not None and reset.tzinfo is None:
        reset = reset.replace(tzinfo=timezone.utc)
    if reset is None or reset.month != now.month or reset.year != now.year:
        user.monthly_chars_used = 0
        user.monthly_chars_reset = now

    user.monthly_chars_used = (user.monthly_chars_used or 0) + n

    db.add(Conversion(
        user_id=user.id, text_preview=text[:200],
        text_length=n, voice=voice, rate=rate, volume=volume,
    ))
    db.commit()


def _check_quota(db: Session, user: User, text_len: int) -> None:
    now = datetime.now(timezone.utc)
    reset = user.monthly_chars_reset
    if reset is not None and reset.tzinfo is None:
        reset = reset.replace(tzinfo=timezone.utc)

    used = user.monthly_chars_used or 0
    if reset is None or reset.month != now.month or reset.year != now.year:
        used = 0

    if used + text_len > MONTHLY_CHAR_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"تجاوزت الحد الشهري ({MONTHLY_CHAR_LIMIT:,} حرف). "
                f"المستخدم حتى الآن: {used:,} حرف. يتجدد في أول الشهر القادم."
            ),
        )


async def _synthesize_to_bytes(text: str, voice: str, rate: str, volume: str, ssml: bool) -> bytes:
    """Synthesize and return MP3 bytes — checks cache first."""
    key = audio_cache.synthesis_key(text, voice, rate, volume, ssml)
    cached = audio_cache.get(key)
    if cached is not None:
        return cached
    try:
        path = await tts_service.synthesize(text=text, voice=voice, rate=rate, volume=volume, ssml=ssml)
    except TTSError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    audio_bytes = path.read_bytes()
    path.unlink(missing_ok=True)
    audio_cache.put(key, audio_bytes)
    return audio_bytes


def _audio_response(audio_bytes: bytes, filename: str = "voiceforge.mp3", cached: bool = False) -> Response:
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Cache": "HIT" if cached else "MISS",
        },
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/voices", response_model=list[VoiceOut])
def voices() -> list[VoiceOut]:
    return tts_service.list_voices()


@router.post("/synthesize")
@limiter.limit("10/minute")
async def synthesize(
    request: Request,
    data: TTSRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Convert text to speech (MP3).  Cache-first — IDEA-02."""
    _check_quota(db, current_user, len(data.text))

    key = audio_cache.synthesis_key(data.text, data.voice, data.rate, data.volume, data.ssml)
    was_cached = audio_cache.get(key) is not None

    audio_bytes = await _synthesize_to_bytes(data.text, data.voice, data.rate, data.volume, data.ssml)
    _record_conversion(db, current_user, data.text, data.voice, data.rate, data.volume)

    return _audio_response(audio_bytes, cached=was_cached)


@router.post("/preview")
@limiter.limit("20/minute")
async def preview(
    request: Request,
    data: PreviewRequest,
    current_user: User = Depends(get_current_user),
) -> Response:
    """Return a short audio sample for voice selection — IDEA-07."""
    try:
        filepath = await tts_service.preview(voice=data.voice, user_text=data.text)
    except TTSError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    audio_bytes = filepath.read_bytes()
    filepath.unlink(missing_ok=True)
    return Response(content=audio_bytes, media_type="audio/mpeg",
                    headers={"Content-Disposition": 'attachment; filename="preview.mp3"'})

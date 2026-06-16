"""Public share-link routes — IDEA-10.

POST  /api/share        → create a 24-hour share (auth required)
GET   /api/share/{uuid}/audio → serve the MP3 publicly
DELETE /api/share/{uuid}      → owner deletes their share
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app import cache as audio_cache
from app.dependencies import get_current_user, get_db
from app.limiter import limiter
from app.models.share import Share
from app.models.user import User
from app.routers.tts import _synthesize_to_bytes
from app.schemas.share import ShareCreate, ShareOut

router = APIRouter(prefix="/api/share", tags=["share"])

SHARE_TTL_HOURS = 24


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("", response_model=ShareOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_share(
    request: Request,
    data: ShareCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShareOut:
    """Synthesise audio (cache-first) and store it as a timed share."""
    audio_bytes = await _synthesize_to_bytes(
        data.text, data.voice, data.rate, data.volume, data.ssml
    )

    uid      = str(uuid4())
    expires  = datetime.now(timezone.utc) + timedelta(hours=SHARE_TTL_HOURS)
    preview  = data.text[:200] if data.text else None

    share = Share(
        uuid=uid,
        user_id=current_user.id,
        text_preview=preview,
        voice=data.voice,
        audio_data=audio_bytes,
        expires_at=expires,
    )
    db.add(share)
    db.commit()

    return ShareOut(uuid=uid, url=f"/s/{uid}", expires_at=expires,
                    text_preview=preview, voice=data.voice)


# ── Audio stream (public) ─────────────────────────────────────────────────────

@router.get("/{uuid}/audio")
def share_audio(uuid: str, db: Session = Depends(get_db)) -> Response:
    """Serve the raw MP3 for a share.  Returns 410 when expired."""
    share = db.query(Share).filter(Share.uuid == uuid).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الرابط غير موجود.")
    if share.is_expired():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="انتهت صلاحية هذا الرابط.")
    return Response(
        content=share.audio_data,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": 'inline; filename="voiceforge-share.mp3"',
            "Cache-Control": "private, max-age=3600",
        },
    )


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_share(
    uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    share = db.query(Share).filter(
        Share.uuid == uuid, Share.user_id == current_user.id
    ).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الرابط غير موجود.")
    db.delete(share)
    db.commit()

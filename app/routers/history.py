"""Conversion history routes — IDEA-06."""

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.conversion import Conversion
from app.models.user import User
from app.schemas.history import HistoryPage

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=HistoryPage)
def list_history(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HistoryPage:
    """Return paginated conversion history for the current user (newest first)."""
    offset = (page - 1) * per_page
    total = db.query(Conversion).filter(Conversion.user_id == current_user.id).count()
    rows = (
        db.query(Conversion)
        .filter(Conversion.user_id == current_user.id)
        .order_by(Conversion.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )
    pages = max(1, math.ceil(total / per_page))
    return HistoryPage(items=rows, total=total, page=page, pages=pages, per_page=per_page)


@router.delete("/{conversion_id}", status_code=204)
def delete_entry(
    conversion_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a single history entry owned by the current user."""
    from fastapi import HTTPException, status

    entry = (
        db.query(Conversion)
        .filter(Conversion.id == conversion_id, Conversion.user_id == current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="السجل غير موجود.")
    db.delete(entry)
    db.commit()

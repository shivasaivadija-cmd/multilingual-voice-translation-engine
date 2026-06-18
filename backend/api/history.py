import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from database.connection import get_session
from services.history_service import HistoryService
from models.schemas import HistoryListResponse, HistoryResponse
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()
history_service = HistoryService()

@router.get("/", response_model=HistoryListResponse)
async def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_language: Optional[str] = Query(None),
    target_language: Optional[str] = Query(None),
    favorites_only: bool = Query(False),
    db: AsyncSession = Depends(get_session)
):
    """Get paginated translation history."""
    return await history_service.get_history(
        db=db, page=page, page_size=page_size,
        source_language=source_language,
        target_language=target_language,
        favorites_only=favorites_only
    )

@router.get("/{entry_id}", response_model=HistoryResponse)
async def get_history_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Get a specific history entry."""
    entry = await history_service.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="History entry not found.")
    return entry

@router.post("/{entry_id}/favorite")
async def toggle_favorite(
    entry_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Toggle favorite status of history entry."""
    entry = await history_service.toggle_favorite(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="History entry not found.")
    return {"id": entry.id, "is_favorite": entry.is_favorite}

@router.delete("/{entry_id}")
async def delete_history_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Delete a history entry."""
    deleted = await history_service.delete_entry(db, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="History entry not found.")
    return {"deleted": True}

@router.delete("/")
async def clear_history(db: AsyncSession = Depends(get_session)):
    """Clear all history."""
    count = await history_service.clear_history(db)
    return {"deleted_count": count}
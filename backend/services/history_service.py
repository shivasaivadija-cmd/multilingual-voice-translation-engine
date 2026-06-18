import logging
import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from database.models import HistoryEntry, FavoriteEntry
from models.schemas import HistoryResponse, HistoryListResponse

logger = logging.getLogger(__name__)

class HistoryService:
    """Service for managing translation history."""

    async def save_entry(
        self,
        db: AsyncSession,
        original_text: str,
        translated_text: str,
        source_language: str,
        target_language: str,
        confidence: float = 0.0,
        duration: float = 0.0,
        model_used: Optional[str] = None,
        session_id: Optional[str] = None,
        word_timestamps: Optional[list] = None,
    ) -> HistoryEntry:
        """Save a new history entry."""
        entry = HistoryEntry(
            id=str(uuid.uuid4()),
            original_text=original_text,
            translated_text=translated_text,
            source_language=source_language,
            target_language=target_language,
            confidence=confidence,
            duration=duration,
            model_used=model_used,
            session_id=session_id,
            word_timestamps=word_timestamps,
        )
        db.add(entry)
        await db.flush()
        logger.info(f"History entry saved: {entry.id}")
        return entry

    async def get_history(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None,
        favorites_only: bool = False,
    ) -> HistoryListResponse:
        """Get paginated history."""
        query = select(HistoryEntry)
        if source_language:
            query = query.where(HistoryEntry.source_language == source_language)
        if target_language:
            query = query.where(HistoryEntry.target_language == target_language)
        if favorites_only:
            query = query.where(HistoryEntry.is_favorite == True)
        query = query.order_by(desc(HistoryEntry.created_at))

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        result = await db.execute(query)
        entries = result.scalars().all()

        return HistoryListResponse(
            items=[HistoryResponse.from_orm(e) for e in entries],
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total
        )

    async def get_entry(self, db: AsyncSession, entry_id: str) -> Optional[HistoryEntry]:
        """Get a single history entry."""
        result = await db.execute(select(HistoryEntry).where(HistoryEntry.id == entry_id))
        return result.scalar_one_or_none()

    async def toggle_favorite(self, db: AsyncSession, entry_id: str) -> Optional[HistoryEntry]:
        """Toggle favorite status."""
        entry = await self.get_entry(db, entry_id)
        if entry:
            entry.is_favorite = not entry.is_favorite
            await db.flush()
        return entry

    async def delete_entry(self, db: AsyncSession, entry_id: str) -> bool:
        """Delete a history entry."""
        entry = await self.get_entry(db, entry_id)
        if entry:
            await db.delete(entry)
            await db.flush()
            return True
        return False

    async def clear_history(self, db: AsyncSession) -> int:
        """Clear all history entries. Returns count deleted."""
        result = await db.execute(select(HistoryEntry))
        entries = result.scalars().all()
        count = len(entries)
        for entry in entries:
            await db.delete(entry)
        await db.flush()
        logger.info(f"Cleared {count} history entries.")
        return count
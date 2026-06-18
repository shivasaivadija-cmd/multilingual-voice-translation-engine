import logging
import json
import csv
import io
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from database.models import HistoryEntry
from models.schemas import ExportRequest
from utils.file_utils import FileManager

logger = logging.getLogger(__name__)

class ExportService:
    """Service for exporting translation history."""

    async def export(
        self,
        db: AsyncSession,
        request: ExportRequest
    ) -> tuple[str, str, str]:
        """
        Export history in requested format.
        Returns (content, filename, mime_type).
        """
        entries = await self._get_entries(db, request)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        if request.format == "json":
            content = self._to_json(entries)
            filename = f"translations_{timestamp}.json"
            mime_type = "application/json"
        elif request.format == "csv":
            content = self._to_csv(entries)
            filename = f"translations_{timestamp}.csv"
            mime_type = "text/csv"
        elif request.format == "txt":
            content = self._to_txt(entries)
            filename = f"translations_{timestamp}.txt"
            mime_type = "text/plain"
        elif request.format == "srt":
            content = self._to_srt(entries)
            filename = f"translations_{timestamp}.srt"
            mime_type = "text/plain"
        else:
            raise ValueError(f"Unsupported export format: {request.format}")

        return content, filename, mime_type

    async def _get_entries(
        self,
        db: AsyncSession,
        request: ExportRequest
    ) -> List[HistoryEntry]:
        query = select(HistoryEntry).order_by(desc(HistoryEntry.created_at))
        if request.start_date:
            query = query.where(HistoryEntry.created_at >= request.start_date)
        if request.end_date:
            query = query.where(HistoryEntry.created_at <= request.end_date)
        if request.language_filter:
            query = query.where(
                (HistoryEntry.source_language == request.language_filter) |
                (HistoryEntry.target_language == request.language_filter)
            )
        result = await db.execute(query)
        return result.scalars().all()

    def _to_json(self, entries: List[HistoryEntry]) -> str:
        data = []
        for e in entries:
            data.append({
                "id": e.id,
                "original_text": e.original_text,
                "translated_text": e.translated_text,
                "source_language": e.source_language,
                "target_language": e.target_language,
                "confidence": e.confidence,
                "duration": e.duration,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "is_favorite": e.is_favorite,
            })
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _to_csv(self, entries: List[HistoryEntry]) -> str:
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["id", "original_text", "translated_text", "source_language",
                       "target_language", "confidence", "created_at", "is_favorite"]
        )
        writer.writeheader()
        for e in entries:
            writer.writerow({
                "id": e.id,
                "original_text": e.original_text,
                "translated_text": e.translated_text,
                "source_language": e.source_language,
                "target_language": e.target_language,
                "confidence": e.confidence,
                "created_at": e.created_at.isoformat() if e.created_at else "",
                "is_favorite": e.is_favorite,
            })
        return output.getvalue()

    def _to_txt(self, entries: List[HistoryEntry]) -> str:
        lines = []
        for e in entries:
            lines.append(f"[{e.created_at.strftime('%Y-%m-%d %H:%M:%S') if e.created_at else 'N/A'}]")
            lines.append(f"Original ({e.source_language}): {e.original_text}")
            lines.append(f"Translated ({e.target_language}): {e.translated_text}")
            lines.append("---")
        return "\n".join(lines)

    def _to_srt(self, entries: List[HistoryEntry]) -> str:
        lines = []
        for i, e in enumerate(entries, 1):
            start_s = i * 5 - 5
            end_s = i * 5
            lines.append(str(i))
            lines.append(f"{self._format_srt_time(start_s)} --> {self._format_srt_time(end_s)}")
            lines.append(e.original_text)
            lines.append(e.translated_text)
            lines.append("")
        return "\n".join(lines)

    def _format_srt_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
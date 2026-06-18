import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from database.connection import get_session
from services.export_service import ExportService
from models.schemas import ExportRequest
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()
export_service = ExportService()

@router.post("/history")
async def export_history(
    body: ExportRequest,
    db: AsyncSession = Depends(get_session)
):
    """Export translation history in requested format."""
    try:
        content, filename, mime_type = await export_service.export(db, body)
        return Response(
            content=content.encode('utf-8'),
            media_type=mime_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail="Export failed.")
import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from database.connection import get_session
from services.settings_service import SettingsService
from models.schemas import SettingsRequest, SettingsResponse
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()
settings_service = SettingsService()

@router.get("/", response_model=List[SettingsResponse])
async def get_all_settings(db: AsyncSession = Depends(get_session)):
    """Get all application settings."""
    return await settings_service.get_all_settings(db)

@router.post("/", response_model=SettingsResponse)
async def update_setting(
    body: SettingsRequest,
    db: AsyncSession = Depends(get_session)
):
    """Update a setting."""
    entry = await settings_service.set_setting(
        db=db, key=body.key, value=body.value, category=body.category
    )
    return SettingsResponse.from_orm(entry)

@router.get("/{key}")
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_session)
):
    """Get a specific setting."""
    value = await settings_service.get_setting(db, key)
    return {"key": key, "value": value}
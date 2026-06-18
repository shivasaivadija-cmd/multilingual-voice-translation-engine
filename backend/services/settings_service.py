import logging
import json
from typing import Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.models import SettingEntry
from models.schemas import SettingsResponse
from datetime import datetime

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS = {
    "theme": "dark",
    "tts_speed": "1.0",
    "tts_pitch": "1.0",
    "tts_volume": "1.0",
    "tts_voice": "en_US-amy-medium",
    "noise_reduction": "true",
    "vad_enabled": "true",
    "vad_sensitivity": "0.5",
    "auto_play_tts": "true",
    "source_language": "auto",
    "target_language": "en",
    "conversation_mode": "single",
    "continuous_mode": "false",
    "show_word_timestamps": "true",
    "font_size": "medium",
    "reduced_motion": "false",
    "high_contrast": "false",
    "gpu_enabled": "true",
    "history_enabled": "true",
    "privacy_mode": "false",
}

class SettingsService:
    """Service for managing user settings."""

    async def get_all_settings(self, db: AsyncSession) -> List[SettingsResponse]:
        """Get all settings."""
        result = await db.execute(select(SettingEntry))
        entries = result.scalars().all()
        settings = {}
        for entry in entries:
            settings[entry.key] = entry
        # Merge with defaults for missing keys
        all_settings = []
        for key, default_value in DEFAULT_SETTINGS.items():
            if key in settings:
                all_settings.append(SettingsResponse.from_orm(settings[key]))
            else:
                all_settings.append(SettingsResponse(
                    key=key,
                    value=default_value,
                    category=self._get_category(key),
                    updated_at=datetime.utcnow()
                ))
        return all_settings

    async def get_setting(self, db: AsyncSession, key: str) -> Optional[Any]:
        """Get a specific setting value."""
        result = await db.execute(select(SettingEntry).where(SettingEntry.key == key))
        entry = result.scalar_one_or_none()
        if entry:
            return self._deserialize(entry.value, entry.value_type)
        return DEFAULT_SETTINGS.get(key)

    async def set_setting(self, db: AsyncSession, key: str, value: Any, category: Optional[str] = None) -> SettingEntry:
        """Set a setting value."""
        result = await db.execute(select(SettingEntry).where(SettingEntry.key == key))
        entry = result.scalar_one_or_none()
        serialized, value_type = self._serialize(value)
        if entry:
            entry.value = serialized
            entry.value_type = value_type
            entry.updated_at = datetime.utcnow()
        else:
            entry = SettingEntry(
                key=key,
                value=serialized,
                value_type=value_type,
                category=category or self._get_category(key),
            )
            db.add(entry)
        await db.flush()
        return entry

    def _serialize(self, value: Any):
        if isinstance(value, bool):
            return str(value).lower(), "bool"
        elif isinstance(value, int):
            return str(value), "int"
        elif isinstance(value, float):
            return str(value), "float"
        elif isinstance(value, (list, dict)):
            return json.dumps(value), "json"
        return str(value), "string"

    def _deserialize(self, value: str, value_type: str) -> Any:
        if value_type == "bool":
            return value.lower() in ("true", "1", "yes")
        elif value_type == "int":
            return int(value)
        elif value_type == "float":
            return float(value)
        elif value_type == "json":
            return json.loads(value)
        return value

    def _get_category(self, key: str) -> str:
        if key.startswith("tts_"):
            return "tts"
        if key in ("noise_reduction", "vad_enabled", "vad_sensitivity"):
            return "audio"
        if key in ("theme", "font_size", "reduced_motion", "high_contrast"):
            return "appearance"
        if key in ("gpu_enabled",):
            return "performance"
        if key in ("history_enabled", "privacy_mode"):
            return "privacy"
        return "general"
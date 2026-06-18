from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, JSON, ForeignKey, Index
)
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
import uuid

class Base(DeclarativeBase):
    pass

def generate_uuid():
    return str(uuid.uuid4())

class HistoryEntry(Base):
    __tablename__ = "history"
    __table_args__ = (
        Index('idx_history_created', 'created_at'),
        Index('idx_history_source_lang', 'source_language'),
        Index('idx_history_target_lang', 'target_language'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    original_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=False)
    source_language = Column(String(20), nullable=False)
    target_language = Column(String(20), nullable=False)
    confidence = Column(Float, default=0.0)
    audio_path = Column(String, nullable=True)
    duration = Column(Float, default=0.0)
    model_used = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_favorite = Column(Boolean, default=False)
    session_id = Column(String, nullable=True)
    word_timestamps = Column(JSON, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)

class FavoriteEntry(Base):
    __tablename__ = "favorites"

    id = Column(String, primary_key=True, default=generate_uuid)
    history_id = Column(String, ForeignKey("history.id"), nullable=False)
    note = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SettingEntry(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default="string")
    category = Column(String(50), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LanguageEntry(Base):
    __tablename__ = "languages"

    code = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    native_name = Column(String(100), nullable=True)
    flag_emoji = Column(String(10), nullable=True)
    nllb_code = Column(String(50), nullable=True)
    whisper_code = Column(String(20), nullable=True)
    tts_supported = Column(Boolean, default=False)
    asr_supported = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

class RecentEntry(Base):
    __tablename__ = "recent"
    __table_args__ = (Index('idx_recent_used', 'last_used'),)

    id = Column(String, primary_key=True, default=generate_uuid)
    source_language = Column(String(20), nullable=False)
    target_language = Column(String(20), nullable=False)
    use_count = Column(Integer, default=1)
    last_used = Column(DateTime, default=datetime.utcnow)

class ConversationEntry(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String(200), nullable=True)
    source_language = Column(String(20), nullable=False)
    target_language = Column(String(20), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    turn_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    metadata_ = Column("metadata", JSON, nullable=True)

class AnalyticsEntry(Base):
    __tablename__ = "analytics"

    id = Column(String, primary_key=True, default=generate_uuid)
    event_type = Column(String(50), nullable=False)
    source_language = Column(String(20), nullable=True)
    target_language = Column(String(20), nullable=True)
    duration = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    model_used = Column(String(100), nullable=True)
    latency_ms = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metadata_ = Column("metadata", JSON, nullable=True)

class ModelEntry(Base):
    __tablename__ = "models"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(200), unique=True, nullable=False)
    model_type = Column(String(50), nullable=False)  # asr, translation, tts, vad
    path = Column(String(500), nullable=True)
    size_mb = Column(Float, nullable=True)
    is_downloaded = Column(Boolean, default=False)
    is_active = Column(Boolean, default=False)
    download_url = Column(String(500), nullable=True)
    version = Column(String(50), nullable=True)
    languages = Column(JSON, nullable=True)
    performance_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)

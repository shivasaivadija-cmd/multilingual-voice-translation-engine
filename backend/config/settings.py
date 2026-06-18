from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    WORKERS: int = 1

    @field_validator('DEBUG', mode='before')
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes')
        return bool(v)

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/translator.db"
    DATABASE_ECHO: bool = False

    # Models
    MODELS_DIR: str = "./models"
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "auto"  # auto, cuda, cpu
    WHISPER_COMPUTE_TYPE: str = "auto"  # auto, float16, int8
    WHISPER_BEAM_SIZE: int = 5
    WHISPER_VAD_FILTER: bool = True
    WHISPER_LANGUAGE: Optional[str] = None  # None = auto detect

    # Translation
    TRANSLATION_MODEL: str = "marian"  # nllb-200, marian
    NLLB_MODEL_NAME: str = "facebook/nllb-200-distilled-600M"
    MARIAN_MODEL_PREFIX: str = "Helsinki-NLP/opus-mt"
    TRANSLATION_MAX_LENGTH: int = 512
    TRANSLATION_BATCH_SIZE: int = 1

    # TTS
    TTS_ENGINE: str = "piper"  # piper, coqui
    TTS_VOICE: str = "en_US-amy-medium"
    TTS_SPEED: float = 1.0
    TTS_PITCH: float = 1.0
    TTS_VOLUME: float = 1.0
    PIPER_MODELS_DIR: str = "./models/piper"
    COQUI_MODELS_DIR: str = "./models/coqui"

    # Audio
    SAMPLE_RATE: int = 16000
    CHUNK_SIZE: int = 1024
    VAD_THRESHOLD: float = 0.5
    VAD_MIN_SILENCE_MS: int = 500
    VAD_SPEECH_PAD_MS: int = 400
    NOISE_REDUCTION_ENABLED: bool = True
    AGC_ENABLED: bool = True

    # Language Detection
    LANG_DETECT_MODEL: str = "lingua"  # lingua, fasttext
    FASTTEXT_MODEL_PATH: str = "./models/fasttext/lid.176.bin"

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60

    # Security
    SECRET_KEY: str = "change-this-secret-key-in-production-please"
    ENCRYPT_HISTORY: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # Export
    EXPORT_DIR: str = "./exports"
    TEMP_DIR: str = "./temp"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

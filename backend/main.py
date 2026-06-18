import uvicorn
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import get_settings
from database.connection import init_db, close_db
from api.speech import router as speech_router
from api.translation import router as translation_router
from api.tts import router as tts_router
from api.history import router as history_router
from api.settings import router as settings_router
from api.health import router as health_router
from api.export import router as export_router
from websocket.handler import router as ws_router
from middleware.rate_limiter import RateLimitMiddleware
from middleware.logging_middleware import RequestLoggingMiddleware
from services.model_manager import ModelManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/app.log', mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting AI Voice Translator Pro...")
    os.makedirs('logs', exist_ok=True)
    os.makedirs('models', exist_ok=True)
    os.makedirs('temp', exist_ok=True)
    os.makedirs('exports', exist_ok=True)
    await init_db()
    settings = get_settings()
    model_manager = ModelManager()
    app.state.model_manager = model_manager
    await model_manager.initialize()
    logger.info("All services initialized. Server is ready.")
    yield
    logger.info("Shutting down AI Voice Translator Pro...")
    await model_manager.cleanup()
    await close_db()
    logger.info("Shutdown complete.")

settings = get_settings()

app = FastAPI(
    title="AI Voice Translator Pro",
    description="Enterprise-grade AI Voice Translation API with real-time streaming, Whisper ASR, NLLB-200 translation, and Piper TTS.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Include routers
app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(speech_router, prefix="/api/speech", tags=["Speech"])
app.include_router(translation_router, prefix="/api/translation", tags=["Translation"])
app.include_router(tts_router, prefix="/api/tts", tags=["TTS"])
app.include_router(history_router, prefix="/api/history", tags=["History"])
app.include_router(settings_router, prefix="/api/settings", tags=["Settings"])
app.include_router(export_router, prefix="/api/export", tags=["Export"])
app.include_router(ws_router, tags=["WebSocket"])

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
        ws_ping_interval=20,
        ws_ping_timeout=20,
    )

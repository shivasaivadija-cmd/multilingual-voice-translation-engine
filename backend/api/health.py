import time
import logging
from fastapi import APIRouter, Request
from models.schemas import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_start_time = time.time()

@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """Health check endpoint with model and system status."""
    model_manager = request.app.state.model_manager
    status = model_manager.get_status()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime=status["uptime"],
        models_loaded=status["models_loaded"],
        gpu_available=status["gpu_available"],
        gpu_name=status.get("gpu_name"),
        memory_usage_mb=status["memory_usage_mb"],
        cpu_percent=status["cpu_percent"],
    )
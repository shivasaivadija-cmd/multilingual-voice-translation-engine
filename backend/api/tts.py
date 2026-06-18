import logging
from fastapi import APIRouter, Request, HTTPException
from models.schemas import TTSRequest, TTSResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/synthesize", response_model=TTSResponse)
async def synthesize_speech(
    request: Request,
    body: TTSRequest
):
    """Synthesize speech from text."""
    try:
        model_manager = request.app.state.model_manager
        if not model_manager.tts_pipeline:
            raise HTTPException(status_code=503, detail="TTS engine not ready.")
        result = await model_manager.tts_pipeline.synthesize(body)
        return result
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"TTS endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")

@router.get("/voices")
async def list_voices(request: Request):
    """List available TTS voices."""
    model_manager = request.app.state.model_manager
    voices = []
    if model_manager.piper:
        voices.extend(model_manager.piper.list_available_voices())
    return {"voices": voices, "total": len(voices)}
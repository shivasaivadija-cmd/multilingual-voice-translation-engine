import logging
import time
from typing import Optional
from .piper_engine import PiperEngine
from .coqui_engine import CoquiEngine
from models.schemas import TTSRequest, TTSResponse

logger = logging.getLogger(__name__)

class TTSPipeline:
    """
    Unified TTS pipeline.
    Priority: Piper → Coqui → Error
    """

    def __init__(self, piper: PiperEngine, coqui: CoquiEngine):
        self.piper = piper
        self.coqui = coqui

    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """Synthesize speech using best available engine."""
        # Try Piper first (fastest)
        if self.piper.is_available:
            try:
                return await self.piper.synthesize(
                    text=request.text,
                    language=request.language,
                    voice=request.voice,
                    speed=request.speed,
                    pitch=request.pitch,
                    volume=request.volume,
                )
            except Exception as e:
                logger.warning(f"Piper TTS failed, trying Coqui: {e}")

        # Try Coqui fallback
        if self.coqui.is_loaded:
            try:
                return await self.coqui.synthesize(
                    text=request.text,
                    language=request.language,
                    speed=request.speed,
                    volume=request.volume,
                )
            except Exception as e:
                logger.error(f"Coqui TTS also failed: {e}")

        raise RuntimeError(
            "No TTS engine available. Install Piper or Coqui TTS."
        )

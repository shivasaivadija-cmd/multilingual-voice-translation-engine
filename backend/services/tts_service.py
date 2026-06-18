import logging
from models.schemas import TTSRequest, TTSResponse
from tts.pipeline import TTSPipeline

logger = logging.getLogger(__name__)

class TTSService:
    """High-level text-to-speech service."""

    def __init__(self, pipeline: TTSPipeline):
        self.pipeline = pipeline

    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """Synthesize speech from text."""
        logger.info(
            f"TTS synthesis: lang={request.language}, "
            f"voice={request.voice}, len={len(request.text)}"
        )
        result = await self.pipeline.synthesize(request)
        logger.info(
            f"TTS complete: duration={result.duration:.2f}s, "
            f"voice={result.voice_used}, time={result.processing_time_ms:.0f}ms"
        )
        return result
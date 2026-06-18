import logging
from typing import Optional
from models.schemas import TranslationRequest, TranslationResponse
from translation.pipeline import TranslationPipeline

logger = logging.getLogger(__name__)

class TranslationService:
    """High-level translation service."""

    def __init__(self, pipeline: TranslationPipeline):
        self.pipeline = pipeline

    async def translate(self, request: TranslationRequest) -> TranslationResponse:
        """Translate text."""
        logger.info(
            f"Translating: {request.source_language} -> {request.target_language} "
            f"({len(request.text)} chars)"
        )
        result = await self.pipeline.translate(request)
        logger.info(
            f"Translation complete using {result.model_used} "
            f"({result.processing_time_ms:.0f}ms)"
        )
        return result

    def detect_language(self, text: str) -> Optional[str]:
        """Detect language of text."""
        return self.pipeline.detect_language(text)
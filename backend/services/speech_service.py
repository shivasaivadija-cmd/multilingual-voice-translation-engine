import logging
import uuid
from typing import Optional
from fastapi import Request
from models.schemas import TranscriptionResponse, TranscriptionRequest
from speech.pipeline import SpeechPipeline

logger = logging.getLogger(__name__)

class SpeechService:
    """High-level speech recognition service."""

    def __init__(self, pipeline: SpeechPipeline):
        self.pipeline = pipeline

    async def transcribe_file(
        self,
        audio_bytes: bytes,
        request_params: TranscriptionRequest,
        session_id: Optional[str] = None,
    ) -> TranscriptionResponse:
        """Transcribe uploaded audio file."""
        if session_id is None:
            session_id = str(uuid.uuid4())
        logger.info(f"[{session_id}] Transcribing audio ({len(audio_bytes) / 1024:.1f}KB)")
        result = await self.pipeline.process_audio_bytes(
            audio_bytes=audio_bytes,
            session_id=session_id,
            language=request_params.language,
        )
        logger.info(f"[{session_id}] Transcription complete: '{result.text[:50]}...' ({result.confidence:.2f})")
        return result

    def reset_session(self, session_id: str) -> None:
        """Reset pipeline state for a session."""
        self.pipeline.reset()
        logger.info(f"Session {session_id} reset.")
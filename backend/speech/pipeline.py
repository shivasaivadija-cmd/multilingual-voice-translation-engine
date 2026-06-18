import numpy as np
import asyncio
import logging
import time
import uuid
from typing import Optional, AsyncGenerator, Dict, Any, Callable
from collections import deque
from config.settings import get_settings
from .audio_processor import AudioPreprocessor
from .vad import VoiceActivityDetector
from .whisper_engine import WhisperEngine
from models.schemas import TranscriptionResponse, StreamingTranscription
from utils.text_utils import TextProcessor

logger = logging.getLogger(__name__)
settings = get_settings()

class SpeechPipeline:
    """
    Full speech processing pipeline:
    Audio → Preprocess → VAD → Buffer → Whisper → Text
    Supports streaming, adaptive buffering, confidence scoring.
    """

    def __init__(
        self,
        whisper: WhisperEngine,
        vad: VoiceActivityDetector,
        preprocessor: AudioPreprocessor
    ):
        self.whisper = whisper
        self.vad = vad
        self.preprocessor = preprocessor
        self.sample_rate = settings.SAMPLE_RATE

        # Streaming state
        self._audio_buffer: deque = deque(maxlen=int(self.sample_rate * 30))  # 30s max
        self._speech_buffer: list = []
        self._is_listening = False
        self._silence_duration = 0.0
        self._speech_detected = False
        self._last_speech_time = 0.0

        # Adaptive chunking
        self._min_chunk_ms = 500
        self._max_chunk_ms = 4000
        self._dynamic_threshold = settings.VAD_THRESHOLD

        logger.info("SpeechPipeline initialized.")

    async def process_audio_bytes(
        self,
        audio_bytes: bytes,
        session_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> TranscriptionResponse:
        """Process raw audio bytes (full file, not streaming)."""
        # Convert to numpy
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        return await self.process_audio_array(audio, session_id=session_id, language=language)

    async def process_audio_array(
        self,
        audio: np.ndarray,
        session_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> TranscriptionResponse:
        """Process a full audio array through the pipeline."""
        # Step 1: Preprocess
        audio = self.preprocessor.process(audio)

        # Step 2: Get speech segments
        segments = self.vad.get_speech_segments(audio)
        if not segments:
            # No speech detected, still try transcription
            logger.info("No speech segments detected by VAD, attempting full transcription.")
            return await self.whisper.transcribe(
                audio,
                language=language,
                word_timestamps=True,
                vad_filter=True,
            )

        # Step 3: Transcribe speech segments
        result = await self.whisper.transcribe(
            audio,
            language=language,
            word_timestamps=True,
            vad_filter=True,
        )
        return result

    async def stream_audio_chunks(
        self,
        audio_chunks: AsyncGenerator[bytes, None],
        session_id: str,
        language: Optional[str] = None,
        on_partial: Optional[Callable] = None,
        on_final: Optional[Callable] = None,
    ) -> None:
        """
        Stream audio chunk by chunk.
        Emits partial and final transcription callbacks.
        """
        accumulated_audio = np.array([], dtype=np.float32)
        last_transcription_time = time.time()
        sequence_number = 0
        silence_frames = 0
        silence_threshold_frames = int(settings.VAD_MIN_SILENCE_MS / 30)  # at 30ms frames

        async for chunk_bytes in audio_chunks:
            chunk = np.frombuffer(chunk_bytes, dtype=np.int16).astype(np.float32) / 32768.0

            # Preprocess chunk
            chunk = self.preprocessor.process(chunk)

            # VAD check
            vad_prob = self.vad.is_speech(chunk)
            is_speech = vad_prob > settings.VAD_THRESHOLD

            if is_speech:
                accumulated_audio = np.concatenate([accumulated_audio, chunk])
                silence_frames = 0
                self._speech_detected = True

                # Emit partial every 500ms of accumulated speech
                elapsed = time.time() - last_transcription_time
                min_audio_s = settings.VAD_MIN_SILENCE_MS / 1000
                if elapsed >= 0.5 and len(accumulated_audio) / self.sample_rate >= 0.5:
                    try:
                        partial_result = await self.whisper.transcribe(
                            accumulated_audio,
                            language=language,
                            beam_size=3,
                            word_timestamps=False,
                            vad_filter=False,
                        )
                        if partial_result.text and on_partial:
                            streaming = StreamingTranscription(
                                text=partial_result.text,
                                is_partial=True,
                                confidence=partial_result.confidence,
                                language=partial_result.language,
                                language_probability=partial_result.language_probability,
                                session_id=session_id,
                                sequence_number=sequence_number
                            )
                            await on_partial(streaming)
                            sequence_number += 1
                            last_transcription_time = time.time()
                    except Exception as e:
                        logger.warning(f"Partial transcription failed: {e}")
            else:
                silence_frames += 1
                if self._speech_detected and silence_frames >= silence_threshold_frames:
                    # End of utterance — run final transcription
                    if len(accumulated_audio) / self.sample_rate >= 0.3:  # min 300ms
                        try:
                            final_result = await self.whisper.transcribe(
                                accumulated_audio,
                                language=language,
                                beam_size=settings.WHISPER_BEAM_SIZE,
                                word_timestamps=True,
                                vad_filter=False,
                            )
                            if final_result.text and on_final:
                                streaming = StreamingTranscription(
                                    text=final_result.text,
                                    is_partial=False,
                                    confidence=final_result.confidence,
                                    language=final_result.language,
                                    language_probability=final_result.language_probability,
                                    word_timestamps=final_result.word_timestamps,
                                    session_id=session_id,
                                    sequence_number=sequence_number
                                )
                                await on_final(streaming)
                                sequence_number += 1
                        except Exception as e:
                            logger.error(f"Final transcription failed: {e}")

                    # Reset state
                    accumulated_audio = np.array([], dtype=np.float32)
                    self._speech_detected = False
                    silence_frames = 0
                    last_transcription_time = time.time()
                    self.vad.reset()

        # Handle remaining audio
        if self._speech_detected and len(accumulated_audio) / self.sample_rate >= 0.3:
            try:
                final_result = await self.whisper.transcribe(
                    accumulated_audio,
                    language=language,
                    beam_size=settings.WHISPER_BEAM_SIZE,
                    word_timestamps=True,
                    vad_filter=False,
                )
                if final_result.text and on_final:
                    streaming = StreamingTranscription(
                        text=final_result.text,
                        is_partial=False,
                        confidence=final_result.confidence,
                        language=final_result.language,
                        language_probability=final_result.language_probability,
                        word_timestamps=final_result.word_timestamps,
                        session_id=session_id,
                        sequence_number=sequence_number
                    )
                    await on_final(streaming)
            except Exception as e:
                logger.error(f"Final chunk transcription failed: {e}")

    def reset(self) -> None:
        """Reset pipeline state."""
        self._speech_buffer.clear()
        self._audio_buffer.clear()
        self._speech_detected = False
        self._silence_duration = 0.0
        self.vad.reset()

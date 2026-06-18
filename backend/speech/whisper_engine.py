import numpy as np
import logging
import time
import torch
from typing import Optional, List, Dict, Any, AsyncGenerator
from config.settings import get_settings
from models.schemas import TranscriptionResponse, WordTimestamp

logger = logging.getLogger(__name__)
settings = get_settings()

class WhisperEngine:
    """
    faster-whisper based speech recognition engine.
    Supports Whisper Large v3 with GPU/CPU fallback.
    """

    def __init__(self):
        self.model = None
        self.model_name = settings.WHISPER_MODEL
        self.device = self._determine_device()
        self.compute_type = self._determine_compute_type()
        self.beam_size = settings.WHISPER_BEAM_SIZE
        self.is_loaded = False
        logger.info(f"WhisperEngine configured: model={self.model_name}, device={self.device}, compute={self.compute_type}")

    def _determine_device(self) -> str:
        """Auto-detect best available device."""
        if settings.WHISPER_DEVICE == "auto":
            if torch.cuda.is_available():
                return "cuda"
            try:
                if torch.backends.mps.is_available():
                    return "cpu"  # faster-whisper uses cpu for MPS
            except Exception:
                pass
            return "cpu"
        return settings.WHISPER_DEVICE

    def _determine_compute_type(self) -> str:
        """Auto-detect best compute type."""
        if settings.WHISPER_COMPUTE_TYPE != "auto":
            return settings.WHISPER_COMPUTE_TYPE
        if self.device == "cuda":
            return "float16"
        return "int8"

    async def load(self) -> None:
        """Load the Whisper model."""
        try:
            import os
            # ULTRA-FAST MODE: limit threads to prevent context switching overhead
            os.environ["MKL_NUM_THREADS"] = "2"  # allow 2 threads for parallel ops
            os.environ["OMP_NUM_THREADS"] = "2"
            os.environ["OPENBLAS_NUM_THREADS"] = "2"
            from faster_whisper import WhisperModel
            logger.info(f"Loading Whisper {self.model_name}...")
            start = time.time()
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
                download_root=settings.MODELS_DIR,
                num_workers=1,
            )
            elapsed = time.time() - start
            self.is_loaded = True
            logger.info(f"Whisper {self.model_name} loaded in {elapsed:.1f}s on {self.device}.")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            # Try loading smaller model as fallback
            if self.model_name != "base":
                logger.info("Falling back to Whisper 'base' model...")
                try:
                    from faster_whisper import WhisperModel
                    self.model = WhisperModel(
                        "base",
                        device="cpu",
                        compute_type="int8",
                        download_root=settings.MODELS_DIR,
                    )
                    self.model_name = "base"
                    self.is_loaded = True
                    logger.info("Fallback Whisper 'base' model loaded.")
                except Exception as e2:
                    logger.error(f"Fallback Whisper load also failed: {e2}")
                    raise RuntimeError(f"Could not load any Whisper model: {e2}")

    async def transcribe(
        self,
        audio: np.ndarray,
        language: Optional[str] = None,
        beam_size: int = 3,
        word_timestamps: bool = False,
        vad_filter: bool = True,
        initial_prompt: Optional[str] = None,
    ) -> TranscriptionResponse:
        """Transcribe audio and return full result."""
        if not self.is_loaded or self.model is None:
            raise RuntimeError("Whisper model not loaded.")

        start_time = time.perf_counter()
        # Default prompt suppresses hallucinations on silence/noise
        if initial_prompt is None:
            initial_prompt = "Transcribe spoken words accurately."

        try:
            segments, info = self.model.transcribe(
                audio,
                language=language,
                beam_size=beam_size,
                word_timestamps=word_timestamps,
                vad_filter=vad_filter,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                    threshold=0.45,
                ) if vad_filter else None,
                initial_prompt=initial_prompt,
                temperature=[0.0, 0.2],      # one fallback only — was [0.0, 0.2, 0.4]
                compression_ratio_threshold=2.6,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.5,
                condition_on_previous_text=True,
                without_timestamps=True,
            )

            # Collect segments
            full_text = ""
            all_words = []
            all_segments = []
            total_confidence = 0.0
            segment_count = 0

            for segment in segments:
                full_text += segment.text
                total_confidence += (-segment.avg_logprob if segment.avg_logprob else 0)
                segment_count += 1
                seg_dict = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "avg_logprob": segment.avg_logprob,
                    "no_speech_prob": segment.no_speech_prob,
                }
                if word_timestamps and segment.words:
                    words = [
                        WordTimestamp(
                            word=w.word,
                            start=w.start,
                            end=w.end,
                            probability=w.probability
                        )
                        for w in segment.words
                    ]
                    all_words.extend(words)
                    seg_dict["words"] = [w.dict() for w in words]
                all_segments.append(seg_dict)

            # Confidence estimation (convert from log prob)
            confidence = 0.0
            if segment_count > 0:
                avg_logprob = total_confidence / segment_count
                # Convert log prob to confidence score [0, 1]
                confidence = float(np.exp(-avg_logprob / segment_count)) if segment_count > 0 else 0.5
                confidence = np.clip(confidence, 0.0, 1.0)
            else:
                confidence = 0.5

            processing_time_ms = (time.perf_counter() - start_time) * 1000
            duration = float(info.duration) if hasattr(info, 'duration') else 0.0

            return TranscriptionResponse(
                text=full_text.strip(),
                language=info.language,
                language_probability=float(info.language_probability),
                confidence=float(confidence),
                duration=duration,
                word_timestamps=all_words if all_words else None,
                segments=all_segments,
                is_partial=False,
                processing_time_ms=processing_time_ms
            )

        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            raise

    async def transcribe_streaming(
        self,
        audio: np.ndarray,
        language: Optional[str] = None,
        beam_size: int = 3,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream transcription results segment by segment."""
        if not self.is_loaded or self.model is None:
            raise RuntimeError("Whisper model not loaded.")

        try:
            segments, info = self.model.transcribe(
                audio,
                language=language,
                beam_size=beam_size,
                word_timestamps=True,
                vad_filter=True,
                temperature=0.0,
            )

            for segment in segments:
                words = []
                if segment.words:
                    words = [
                        {"word": w.word, "start": w.start, "end": w.end, "prob": w.probability}
                        for w in segment.words
                    ]
                yield {
                    "text": segment.text.strip(),
                    "start": segment.start,
                    "end": segment.end,
                    "language": info.language,
                    "language_probability": float(info.language_probability),
                    "confidence": float(np.exp(segment.avg_logprob)) if segment.avg_logprob else 0.5,
                    "words": words,
                    "is_partial": False,
                }
        except Exception as e:
            logger.error(f"Streaming transcription error: {e}")
            raise

    def unload(self) -> None:
        """Unload model to free memory."""
        if self.model is not None:
            del self.model
            self.model = None
            self.is_loaded = False
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("Whisper model unloaded.")

    @property
    def device_info(self) -> Dict[str, Any]:
        return {
            "device": self.device,
            "compute_type": self.compute_type,
            "model_name": self.model_name,
            "is_loaded": self.is_loaded,
            "gpu_available": torch.cuda.is_available(),
        }

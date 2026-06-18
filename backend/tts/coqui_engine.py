import logging
import time
import base64
import numpy as np
from typing import Optional, List
from config.settings import get_settings
from models.schemas import TTSResponse
from utils.audio_utils import AudioProcessor

logger = logging.getLogger(__name__)
settings = get_settings()

class CoquiEngine:
    """
    Coqui XTTS TTS engine - multilingual neural TTS.
    Used as fallback when Piper is unavailable.
    """

    def __init__(self):
        self.tts = None
        self.is_loaded = False
        self.current_model = None
        self.sample_rate = 22050
        logger.info("CoquiEngine initialized.")

    async def load(self, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2") -> None:
        """Load Coqui TTS model."""
        try:
            from TTS.api import TTS
            logger.info(f"Loading Coqui TTS: {model_name}...")
            start = time.time()
            self.tts = TTS(model_name=model_name, progress_bar=False)
            self.current_model = model_name
            self.is_loaded = True
            elapsed = time.time() - start
            logger.info(f"Coqui TTS loaded in {elapsed:.1f}s.")
        except ImportError:
            logger.warning("Coqui TTS not installed. Run: pip install TTS")
        except Exception as e:
            logger.error(f"Failed to load Coqui TTS: {e}")

    async def synthesize(
        self,
        text: str,
        language: str = 'en',
        speaker_wav: Optional[str] = None,
        speed: float = 1.0,
        volume: float = 1.0,
    ) -> TTSResponse:
        """Synthesize speech using Coqui XTTS."""
        if not self.is_loaded or self.tts is None:
            raise RuntimeError("Coqui TTS not loaded.")

        start_time = time.perf_counter()

        try:
            import io
            buffer = io.BytesIO()

            # XTTS v2 requires a speaker_wav for voice cloning
            # Use a default speaker if none provided
            tts_kwargs = {
                'text': text,
                'language': language[:2],
                'file_path': None
            }

            if speaker_wav and hasattr(self.tts, 'tts_with_vc'):
                tts_kwargs['speaker_wav'] = speaker_wav

            audio = self.tts.tts(**tts_kwargs)
            if audio is None:
                raise RuntimeError("Coqui TTS returned no audio.")

            if not isinstance(audio, np.ndarray):
                audio = np.array(audio, dtype=np.float32)

            if volume != 1.0:
                audio = np.clip(audio * volume, -1.0, 1.0)

            duration = len(audio) / self.sample_rate
            wav_bytes = AudioProcessor.create_wav_bytes(audio, self.sample_rate)
            audio_b64 = base64.b64encode(wav_bytes).decode('utf-8')

            processing_time_ms = (time.perf_counter() - start_time) * 1000
            return TTSResponse(
                audio_base64=audio_b64,
                sample_rate=self.sample_rate,
                duration=duration,
                voice_used=self.current_model or "xtts_v2",
                processing_time_ms=processing_time_ms
            )
        except Exception as e:
            logger.error(f"Coqui TTS synthesis error: {e}")
            raise

    def unload(self) -> None:
        """Unload model."""
        if self.tts:
            del self.tts
            self.tts = None
            self.is_loaded = False
            logger.info("Coqui TTS unloaded.")

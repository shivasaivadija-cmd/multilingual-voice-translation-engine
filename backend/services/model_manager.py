import logging
import time
import psutil
import torch
from typing import Dict, Any, Optional
from config.settings import get_settings
from speech.whisper_engine import WhisperEngine
from speech.vad import VoiceActivityDetector
from speech.audio_processor import AudioPreprocessor
from speech.pipeline import SpeechPipeline
from translation.nllb import NLLBTranslator
from translation.marian import MarianTranslator
from translation.language_detector import LanguageDetector
from translation.pipeline import TranslationPipeline
from tts.piper_engine import PiperEngine
from tts.coqui_engine import CoquiEngine
from tts.pipeline import TTSPipeline

logger = logging.getLogger(__name__)
settings = get_settings()

class ModelManager:
    """
    Central manager for all AI models.
    Handles loading, initialization, and cleanup.
    """

    def __init__(self):
        self.start_time = time.time()
        # ASR
        self.whisper: Optional[WhisperEngine] = None
        self.vad: Optional[VoiceActivityDetector] = None
        self.preprocessor: Optional[AudioPreprocessor] = None
        self.speech_pipeline: Optional[SpeechPipeline] = None
        # Translation
        self.nllb: Optional[NLLBTranslator] = None
        self.marian: Optional[MarianTranslator] = None
        self.lang_detector: Optional[LanguageDetector] = None
        self.translation_pipeline: Optional[TranslationPipeline] = None
        # TTS
        self.piper: Optional[PiperEngine] = None
        self.coqui: Optional[CoquiEngine] = None
        self.tts_pipeline: Optional[TTSPipeline] = None
        # Status tracking
        self._model_status: Dict[str, bool] = {
            "whisper": False,
            "vad": False,
            "nllb": False,
            "marian": False,
            "piper": False,
            "coqui": False,
        }

    async def initialize(self) -> None:
        """Initialize all models concurrently where possible."""
        import asyncio
        logger.info("Initializing AI models...")

        # Initialize preprocessor and VAD (fast, no network)
        self.preprocessor = AudioPreprocessor()
        self.vad = VoiceActivityDetector()
        self._model_status["vad"] = True

        # Load Whisper
        self.whisper = WhisperEngine()
        try:
            await self.whisper.load()
            self._model_status["whisper"] = True
        except Exception as e:
            logger.error(f"Whisper initialization failed: {e}")

        # Initialize speech pipeline
        self.speech_pipeline = SpeechPipeline(
            whisper=self.whisper,
            vad=self.vad,
            preprocessor=self.preprocessor
        )

        # Initialize NLLB translator (primary — supports 200+ languages including Telugu)
        if settings.TRANSLATION_MODEL == "nllb-200":
            self.nllb = NLLBTranslator()
            try:
                await self.nllb.load()
                self._model_status["nllb"] = True
                logger.info("NLLB-200 loaded as primary translation model.")
            except Exception as e:
                logger.warning(f"NLLB initialization failed, falling back to Marian: {e}")
                self.nllb = None
        else:
            logger.info("NLLB model skipped (using Marian instead)")

        # Initialize Marian (on-demand, no preload)
        self.marian = MarianTranslator()
        self._model_status["marian"] = True

        # Initialize language detector
        self.lang_detector = LanguageDetector()

        # Initialize translation pipeline
        self.translation_pipeline = TranslationPipeline(
            nllb=self.nllb,
            marian=self.marian,
            detector=self.lang_detector
        )

        # Initialize Piper TTS
        self.piper = PiperEngine()
        self._model_status["piper"] = self.piper.is_available

        # Initialize Coqui TTS (optional)
        self.coqui = CoquiEngine()
        try:
            await self.coqui.load()
            self._model_status["coqui"] = True
        except Exception as e:
            logger.warning(f"Coqui TTS not available: {e}")

        # Initialize TTS pipeline
        self.tts_pipeline = TTSPipeline(piper=self.piper, coqui=self.coqui)

        logger.info(f"Model initialization complete. Status: {self._model_status}")

    async def cleanup(self) -> None:
        """Cleanup all models."""
        if self.whisper:
            self.whisper.unload()
        if self.nllb:
            self.nllb.unload()
        if self.marian:
            self.marian.unload_all()
        if self.coqui:
            self.coqui.unload()
        logger.info("All models cleaned up.")

    def get_status(self) -> Dict[str, Any]:
        """Get current status of all models."""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        cpu_percent = psutil.cpu_percent(interval=0.1)
        gpu_available = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if gpu_available else None

        return {
            "models_loaded": self._model_status.copy(),
            "gpu_available": gpu_available,
            "gpu_name": gpu_name,
            "memory_usage_mb": memory_mb,
            "cpu_percent": cpu_percent,
            "uptime": time.time() - self.start_time,
        }
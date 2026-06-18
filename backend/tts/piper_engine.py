import logging
import time
import os
import struct
import base64
import subprocess
import tempfile
import json
from typing import Optional, Dict, List
from config.settings import get_settings
from models.schemas import TTSResponse
from utils.audio_utils import AudioProcessor
from utils.file_utils import FileManager

logger = logging.getLogger(__name__)
settings = get_settings()

PIPER_VOICES: Dict[str, Dict] = {
    'en': {'voice': 'en_US-amy-medium', 'speaker': None},
    'es': {'voice': 'es_ES-mls-medium', 'speaker': None},
    'fr': {'voice': 'fr_FR-mls-medium', 'speaker': None},
    'de': {'voice': 'de_DE-thorsten-medium', 'speaker': None},
    'it': {'voice': 'it_IT-riccardo-x_low', 'speaker': None},
    'pt': {'voice': 'pt_BR-edresson-low', 'speaker': None},
    'ru': {'voice': 'ru_RU-denis-medium', 'speaker': None},
    'zh': {'voice': 'zh_CN-huayan-medium', 'speaker': None},
    'ja': {'voice': 'ja_JP-kennnichi-medium', 'speaker': None},
    'ko': {'voice': 'ko_KR-voices-medium', 'speaker': 0},
    'nl': {'voice': 'nl_NL-mls-medium', 'speaker': None},
    'pl': {'voice': 'pl_PL-mls-medium', 'speaker': None},
    'uk': {'voice': 'uk_UA-lada-x_low', 'speaker': None},
    'ar': {'voice': 'ar_JO-kareem-medium', 'speaker': None},
    'hi': {'voice': 'hi_IN-hindi_voices-medium', 'speaker': 0},
    'tr': {'voice': 'tr_TR-dfki-medium', 'speaker': None},
    'vi': {'voice': 'vi_VN-25hours_single-low', 'speaker': None},
}

class PiperEngine:
    """
    Piper TTS engine - fast, high-quality local TTS.
    Uses subprocess calls to piper binary.
    """

    def __init__(self):
        self.models_dir = settings.PIPER_MODELS_DIR
        self.piper_binary = self._find_piper_binary()
        self.is_available = self.piper_binary is not None
        self._loaded_voices: Dict[str, str] = {}  # lang -> model path
        os.makedirs(self.models_dir, exist_ok=True)
        logger.info(f"PiperEngine initialized. Binary: {self.piper_binary}, Available: {self.is_available}")

    def _find_piper_binary(self) -> Optional[str]:
        """Find piper binary in PATH or common locations."""
        import shutil
        binary = shutil.which('piper')
        if binary:
            return binary
        # Check common locations
        candidates = [
            './piper/piper',
            './piper/piper.exe',
            '/usr/local/bin/piper',
            os.path.join(settings.MODELS_DIR, 'piper', 'piper'),
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
        return None

    def get_voice_for_language(self, language: str) -> Optional[Dict]:
        """Get voice config for language."""
        lang_code = language.lower()[:2]
        return PIPER_VOICES.get(lang_code)

    def get_model_path(self, voice_name: str) -> str:
        """Get path to piper voice model."""
        return os.path.join(self.models_dir, voice_name, f"{voice_name}.onnx")

    def get_config_path(self, voice_name: str) -> str:
        """Get path to piper voice config."""
        return os.path.join(self.models_dir, voice_name, f"{voice_name}.onnx.json")

    async def synthesize(
        self,
        text: str,
        language: str = 'en',
        voice: Optional[str] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
        volume: float = 1.0,
    ) -> TTSResponse:
        """Synthesize speech using Piper."""
        if not self.is_available:
            raise RuntimeError("Piper binary not found.")

        start_time = time.perf_counter()
        voice_config = self.get_voice_for_language(language)
        voice_name = voice or (voice_config['voice'] if voice_config else 'en_US-amy-medium')

        model_path = self.get_model_path(voice_name)
        config_path = self.get_config_path(voice_name)

        if not os.path.exists(model_path):
            # Try default English voice as fallback
            voice_name = 'en_US-amy-medium'
            model_path = self.get_model_path(voice_name)
            config_path = self.get_config_path(voice_name)
            if not os.path.exists(model_path):
                raise RuntimeError(
                    f"Piper voice model not found: {model_path}. "
                    f"Run scripts/download_models.py to download voices."
                )

        # Create temp output file
        output_path = FileManager.get_temp_file(suffix='.wav', prefix='tts_')
        try:
            # Build piper command
            cmd = [
                self.piper_binary,
                '--model', model_path,
                '--config', config_path,
                '--output_file', output_path,
                '--length-scale', str(1.0 / speed),  # length-scale is inverse of speed
                '--sentence-silence', '0.3',
            ]
            if voice_config and voice_config.get('speaker') is not None:
                cmd.extend(['--speaker', str(voice_config['speaker'])])

            # Run piper
            process = subprocess.run(
                cmd,
                input=text.encode('utf-8'),
                capture_output=True,
                timeout=30
            )

            if process.returncode != 0:
                error = process.stderr.decode('utf-8', errors='replace')
                raise RuntimeError(f"Piper failed (rc={process.returncode}): {error}")

            # Read and process output audio
            with open(output_path, 'rb') as f:
                wav_bytes = f.read()

            import numpy as np
            import wave
            import io
            with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
                sample_rate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

            # Apply volume
            if volume != 1.0:
                audio = np.clip(audio * volume, -1.0, 1.0)

            duration = len(audio) / sample_rate
            audio_bytes = AudioProcessor.create_wav_bytes(audio, sample_rate)
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')

            processing_time_ms = (time.perf_counter() - start_time) * 1000
            return TTSResponse(
                audio_base64=audio_b64,
                sample_rate=sample_rate,
                duration=duration,
                voice_used=voice_name,
                processing_time_ms=processing_time_ms
            )
        finally:
            FileManager.safe_delete(output_path)

    def list_available_voices(self) -> List[Dict]:
        """List all downloaded voice models."""
        voices = []
        if not os.path.exists(self.models_dir):
            return voices
        for voice_dir in os.listdir(self.models_dir):
            model_path = self.get_model_path(voice_dir)
            if os.path.exists(model_path):
                voices.append({
                    'id': voice_dir,
                    'name': voice_dir.replace('_', ' ').replace('-', ' '),
                    'path': model_path,
                    'size_mb': FileManager.get_file_size_mb(model_path)
                })
        return voices

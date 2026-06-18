import numpy as np
import io
import wave
import struct
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Low-level audio utility functions."""

    @staticmethod
    def bytes_to_numpy(audio_bytes: bytes, sample_rate: int = 16000) -> np.ndarray:
        """Convert raw audio bytes (PCM16) to float32 numpy array."""
        try:
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            return audio_array.astype(np.float32) / 32768.0
        except Exception as e:
            logger.error(f"Error converting bytes to numpy: {e}")
            return np.zeros(0, dtype=np.float32)

    @staticmethod
    def numpy_to_bytes(audio_array: np.ndarray) -> bytes:
        """Convert float32 numpy array to PCM16 bytes."""
        audio_int16 = (np.clip(audio_array, -1.0, 1.0) * 32767).astype(np.int16)
        return audio_int16.tobytes()

    @staticmethod
    def create_wav_bytes(audio_array: np.ndarray, sample_rate: int = 16000) -> bytes:
        """Create a WAV file in memory from a numpy array."""
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(AudioProcessor.numpy_to_bytes(audio_array))
        return buffer.getvalue()

    @staticmethod
    def normalize_audio(audio: np.ndarray, target_db: float = -20.0) -> np.ndarray:
        """Normalize audio to target dB level."""
        if len(audio) == 0:
            return audio
        rms = np.sqrt(np.mean(audio ** 2))
        if rms < 1e-8:
            return audio
        target_rms = 10 ** (target_db / 20.0)
        gain = target_rms / rms
        return np.clip(audio * gain, -1.0, 1.0)

    @staticmethod
    def resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Simple linear resampling."""
        if orig_sr == target_sr:
            return audio
        ratio = target_sr / orig_sr
        new_length = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, new_length)
        return np.interp(indices, np.arange(len(audio)), audio)

    @staticmethod
    def split_into_chunks(audio: np.ndarray, chunk_size: int, overlap: int = 0) -> list:
        """Split audio into overlapping chunks."""
        chunks = []
        step = chunk_size - overlap
        for start in range(0, len(audio), step):
            chunk = audio[start:start + chunk_size]
            if len(chunk) > 0:
                chunks.append(chunk)
        return chunks

    @staticmethod
    def compute_rms(audio: np.ndarray) -> float:
        """Compute Root Mean Square energy."""
        if len(audio) == 0:
            return 0.0
        return float(np.sqrt(np.mean(audio ** 2)))

    @staticmethod
    def is_speech(audio: np.ndarray, threshold: float = 0.01) -> bool:
        """Simple energy-based speech detection."""
        return AudioProcessor.compute_rms(audio) > threshold

    @staticmethod
    def apply_noise_gate(audio: np.ndarray, threshold: float = 0.005) -> np.ndarray:
        """Apply a simple noise gate."""
        mask = np.abs(audio) > threshold
        return audio * mask

    @staticmethod
    def auto_gain_control(audio: np.ndarray, target_level: float = 0.3) -> np.ndarray:
        """Apply automatic gain control."""
        peak = np.max(np.abs(audio))
        if peak < 1e-8:
            return audio
        gain = target_level / peak
        gain = np.clip(gain, 0.1, 10.0)  # Limit gain range
        return np.clip(audio * gain, -1.0, 1.0)

    @staticmethod
    def calculate_duration(audio: np.ndarray, sample_rate: int) -> float:
        """Calculate audio duration in seconds."""
        return len(audio) / sample_rate

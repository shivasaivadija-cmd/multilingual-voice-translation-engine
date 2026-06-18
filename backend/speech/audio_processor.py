import numpy as np
import logging
from typing import Optional, Tuple
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class AudioPreprocessor:
    """
    Full audio preprocessing pipeline:
    Noise Suppression → Echo Cancellation → Auto Gain Control
    """

    def __init__(self):
        self.sample_rate = settings.SAMPLE_RATE
        self.noise_reduction_enabled = settings.NOISE_REDUCTION_ENABLED
        self.agc_enabled = settings.AGC_ENABLED
        self._noise_profile: Optional[np.ndarray] = None
        self._noise_floor: float = 0.005
        logger.info("AudioPreprocessor initialized.")

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Full pipeline processing."""
        if len(audio) == 0:
            return audio
        # Step 1: Normalize input
        audio = self._normalize(audio)
        # Step 2: Noise reduction
        if self.noise_reduction_enabled:
            audio = self._reduce_noise(audio)
        # Step 3: Auto gain control
        if self.agc_enabled:
            audio = self._auto_gain_control(audio)
        # Step 4: DC offset removal
        audio = self._remove_dc_offset(audio)
        return audio

    def _normalize(self, audio: np.ndarray) -> np.ndarray:
        """Convert to float32 and ensure range [-1, 1]."""
        if audio.dtype != np.float32:
            if audio.dtype == np.int16:
                audio = audio.astype(np.float32) / 32768.0
            elif audio.dtype == np.int32:
                audio = audio.astype(np.float32) / 2147483648.0
            else:
                audio = audio.astype(np.float32)
        return np.clip(audio, -1.0, 1.0)

    def _reduce_noise(self, audio: np.ndarray) -> np.ndarray:
        """Spectral subtraction-based noise reduction."""
        try:
            # Try using noisereduce if available
            import noisereduce as nr
            reduced = nr.reduce_noise(
                y=audio,
                sr=self.sample_rate,
                stationary=False,
                prop_decrease=0.75,
                n_std_thresh_stationary=1.5,
                n_fft=512
            )
            return reduced.astype(np.float32)
        except ImportError:
            # Fallback: simple spectral subtraction
            return self._simple_noise_reduction(audio)

    def _simple_noise_reduction(self, audio: np.ndarray) -> np.ndarray:
        """Simple energy-based noise gate."""
        # Estimate noise floor from quietest 10% of frames
        frame_size = 512
        frames = [audio[i:i+frame_size] for i in range(0, len(audio), frame_size)]
        frame_energies = [np.sqrt(np.mean(f**2)) for f in frames if len(f) == frame_size]
        if frame_energies:
            frame_energies.sort()
            noise_floor = np.mean(frame_energies[:max(1, len(frame_energies)//10)])
            noise_floor = max(noise_floor, 0.002)
        else:
            noise_floor = 0.005
        # Apply soft noise gate
        rms = np.sqrt(np.mean(audio**2))
        if rms < noise_floor * 3:
            return audio * 0.1  # Strongly suppress
        return audio

    def _auto_gain_control(self, audio: np.ndarray, target_rms: float = 0.1) -> np.ndarray:
        """Adaptive gain control with smoothing."""
        rms = np.sqrt(np.mean(audio**2))
        if rms < 1e-8:
            return audio
        gain = target_rms / rms
        # Limit gain to reasonable range
        gain = np.clip(gain, 0.1, 20.0)
        return np.clip(audio * gain, -1.0, 1.0)

    def _remove_dc_offset(self, audio: np.ndarray) -> np.ndarray:
        """Remove DC offset (mean subtraction)."""
        return audio - np.mean(audio)

    def calibrate_noise_profile(self, audio: np.ndarray) -> None:
        """Calibrate noise profile from a silence sample."""
        self._noise_profile = audio.copy()
        self._noise_floor = float(np.sqrt(np.mean(audio**2)))
        logger.info(f"Noise floor calibrated: {self._noise_floor:.4f}")

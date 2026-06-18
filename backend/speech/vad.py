import numpy as np
import logging
import torch
from typing import List, Tuple, Optional
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class VoiceActivityDetector:
    """
    Silero VAD-based voice activity detection.
    Falls back to energy-based VAD if model unavailable.
    """

    def __init__(self):
        self.model = None
        self.utils = None
        self.sample_rate = settings.SAMPLE_RATE
        self.threshold = settings.VAD_THRESHOLD
        self.min_silence_ms = settings.VAD_MIN_SILENCE_MS
        self.speech_pad_ms = settings.VAD_SPEECH_PAD_MS
        self._using_silero = False
        self._load_model()

    def _load_model(self) -> None:
        """Load Silero VAD model."""
        try:
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                verbose=False,
                trust_repo=True
            )
            self.model = model
            self.utils = utils
            self._using_silero = True
            logger.info("Silero VAD loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load Silero VAD: {e}. Using energy-based VAD.")
            self._using_silero = False

    def is_speech(self, audio_chunk: np.ndarray) -> float:
        """
        Returns speech probability [0.0, 1.0] for audio chunk.
        Audio must be 16kHz mono float32.
        """
        if self._using_silero and self.model is not None:
            return self._silero_predict(audio_chunk)
        return self._energy_vad(audio_chunk)

    # Silero VAD requires exactly 512 samples at 16kHz (or 256 at 8kHz)
    _SILERO_FRAME_SIZE = 512

    def _silero_predict(self, audio: np.ndarray) -> float:
        """Run Silero VAD inference, chunking into required 512-sample frames."""
        try:
            if len(audio) < self._SILERO_FRAME_SIZE:
                # Too short — pad to minimum frame size
                audio = np.pad(audio, (0, self._SILERO_FRAME_SIZE - len(audio)))

            probs = []
            for start in range(0, len(audio) - self._SILERO_FRAME_SIZE + 1, self._SILERO_FRAME_SIZE):
                frame = audio[start:start + self._SILERO_FRAME_SIZE]
                tensor = torch.FloatTensor(frame).unsqueeze(0)  # (1, 512)
                with torch.no_grad():
                    prob = self.model(tensor, self.sample_rate).item()
                probs.append(prob)

            return float(max(probs)) if probs else 0.0
        except Exception as e:
            logger.warning(f"Silero inference failed: {e}")
            return self._energy_vad(audio)

    def _energy_vad(self, audio: np.ndarray) -> float:
        """Energy-based VAD fallback."""
        rms = float(np.sqrt(np.mean(audio**2)))
        # Sigmoid-like mapping of energy to probability
        normalized = np.clip(rms / 0.05, 0.0, 1.0)
        return float(normalized)

    def get_speech_segments(
        self,
        audio: np.ndarray,
        return_seconds: bool = True
    ) -> List[dict]:
        """Get speech segments from audio."""
        if self._using_silero and self.utils is not None:
            return self._get_silero_segments(audio, return_seconds)
        return self._get_energy_segments(audio, return_seconds)

    def _get_silero_segments(self, audio: np.ndarray, return_seconds: bool) -> List[dict]:
        """Get speech segments using Silero VAD."""
        try:
            (get_speech_ts, _, _, _, _) = self.utils
            tensor = torch.FloatTensor(audio)
            speech_timestamps = get_speech_ts(
                tensor,
                self.model,
                sampling_rate=self.sample_rate,
                threshold=self.threshold,
                min_silence_duration_ms=self.min_silence_ms,
                speech_pad_ms=self.speech_pad_ms
            )
            if return_seconds:
                return [
                    {"start": s['start'] / self.sample_rate, "end": s['end'] / self.sample_rate}
                    for s in speech_timestamps
                ]
            return speech_timestamps
        except Exception as e:
            logger.warning(f"Silero segments failed: {e}")
            return self._get_energy_segments(audio, return_seconds)

    def _get_energy_segments(self, audio: np.ndarray, return_seconds: bool) -> List[dict]:
        """Simple energy-based segmentation."""
        frame_size = int(self.sample_rate * 0.03)  # 30ms frames
        segments = []
        in_speech = False
        speech_start = 0
        silence_count = 0
        silence_frames = int(self.min_silence_ms / 30)

        for i in range(0, len(audio), frame_size):
            frame = audio[i:i + frame_size]
            if len(frame) < frame_size:
                break
            energy = np.sqrt(np.mean(frame**2))
            is_speech = energy > 0.02

            if is_speech and not in_speech:
                speech_start = i
                in_speech = True
                silence_count = 0
            elif not is_speech and in_speech:
                silence_count += 1
                if silence_count >= silence_frames:
                    end = i - silence_count * frame_size + frame_size
                    if return_seconds:
                        segments.append({
                            "start": speech_start / self.sample_rate,
                            "end": end / self.sample_rate
                        })
                    else:
                        segments.append({"start": speech_start, "end": end})
                    in_speech = False
            elif is_speech:
                silence_count = 0

        if in_speech:
            if return_seconds:
                segments.append({
                    "start": speech_start / self.sample_rate,
                    "end": len(audio) / self.sample_rate
                })
            else:
                segments.append({"start": speech_start, "end": len(audio)})

        return segments

    def reset(self) -> None:
        """Reset VAD state."""
        if self._using_silero and self.model is not None:
            try:
                self.model.reset_states()
            except Exception:
                pass

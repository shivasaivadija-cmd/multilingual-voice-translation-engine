import pytest
import numpy as np
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.audio_utils import AudioProcessor

class TestTTSAudioProcessing:
    def test_wav_bytes_valid_format(self):
        import wave
        import io
        audio = np.sin(np.linspace(0, 2*np.pi*440, 22050)).astype(np.float32)
        wav_bytes = AudioProcessor.create_wav_bytes(audio, 22050)
        with wave.open(io.BytesIO(wav_bytes)) as wf:
            assert wf.getframerate() == 22050
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2

    def test_auto_gain_control_increases_quiet_audio(self):
        quiet_audio = np.ones(1000, dtype=np.float32) * 0.001
        louder = AudioProcessor.auto_gain_control(quiet_audio, target_level=0.3)
        assert np.max(np.abs(louder)) > np.max(np.abs(quiet_audio))

    def test_auto_gain_control_limits_range(self):
        quiet_audio = np.ones(1000, dtype=np.float32) * 0.001
        louder = AudioProcessor.auto_gain_control(quiet_audio, target_level=0.3)
        assert louder.max() <= 1.0
        assert louder.min() >= -1.0

class TestPiperVoiceConfig:
    def test_piper_voices_dict_structure(self):
        from tts.piper_engine import PIPER_VOICES
        assert 'en' in PIPER_VOICES
        for lang, config in PIPER_VOICES.items():
            assert 'voice' in config
            assert len(lang) == 2

    def test_piper_engine_init(self):
        from tts.piper_engine import PiperEngine
        engine = PiperEngine()
        # Should not raise
        assert hasattr(engine, 'is_available')
        assert hasattr(engine, 'models_dir')

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
import pytest
import numpy as np
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.audio_utils import AudioProcessor
from utils.text_utils import TextProcessor
from speech.audio_processor import AudioPreprocessor

class TestAudioProcessor:
    def test_bytes_to_numpy_returns_float32(self):
        audio_int16 = np.array([0, 16384, -16384, 32767], dtype=np.int16)
        audio_bytes = audio_int16.tobytes()
        result = AudioProcessor.bytes_to_numpy(audio_bytes)
        assert result.dtype == np.float32
        assert len(result) == 4
        assert -1.0 <= result.max() <= 1.0
        assert -1.0 <= result.min() <= 1.0

    def test_numpy_to_bytes_roundtrip(self):
        original = np.array([0.5, -0.5, 0.0, 1.0], dtype=np.float32)
        as_bytes = AudioProcessor.numpy_to_bytes(original)
        recovered = AudioProcessor.bytes_to_numpy(as_bytes)
        np.testing.assert_allclose(original, recovered, atol=0.001)

    def test_create_wav_bytes_produces_valid_wav(self):
        import io
        import wave
        audio = np.random.randn(16000).astype(np.float32) * 0.1
        wav_bytes = AudioProcessor.create_wav_bytes(audio, 16000)
        assert wav_bytes[:4] == b'RIFF'
        with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
            assert wf.getnchannels() == 1
            assert wf.getframerate() == 16000
            assert wf.getsampwidth() == 2

    def test_normalize_audio(self):
        audio = np.array([0.001, 0.002, -0.001], dtype=np.float32)
        normalized = AudioProcessor.normalize_audio(audio, target_db=-20.0)
        assert len(normalized) == 3
        assert all(-1.0 <= v <= 1.0 for v in normalized)

    def test_compute_rms_silent(self):
        audio = np.zeros(1000, dtype=np.float32)
        rms = AudioProcessor.compute_rms(audio)
        assert rms == 0.0

    def test_compute_rms_sine(self):
        t = np.linspace(0, 1, 16000)
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        rms = AudioProcessor.compute_rms(audio)
        assert 0.6 < rms < 0.8  # sqrt(2)/2 ≈ 0.707

    def test_split_into_chunks(self):
        audio = np.ones(16000, dtype=np.float32)
        chunks = AudioProcessor.split_into_chunks(audio, chunk_size=4000)
        assert len(chunks) == 4

    def test_calculate_duration(self):
        audio = np.zeros(32000, dtype=np.float32)
        duration = AudioProcessor.calculate_duration(audio, 16000)
        assert duration == pytest.approx(2.0)

class TestTextProcessor:
    def test_clean_transcript_strips_whitespace(self):
        result = TextProcessor.clean_transcript("  hello world  ")
        assert result == "hello world"

    def test_clean_transcript_removes_artifacts(self):
        result = TextProcessor.clean_transcript("[BLANK_AUDIO] hello")
        assert "BLANK_AUDIO" not in result

    def test_restore_punctuation_capitalizes(self):
        result = TextProcessor.restore_punctuation("hello world")
        assert result[0].isupper()

    def test_restore_punctuation_adds_period(self):
        result = TextProcessor.restore_punctuation("hello world")
        assert result.endswith('.')

    def test_split_into_sentences(self):
        text = "Hello world. How are you? I am fine."
        sentences = TextProcessor.split_into_sentences(text)
        assert len(sentences) >= 2

    def test_count_words(self):
        assert TextProcessor.count_words("hello world foo") == 3

    def test_truncate_text(self):
        long_text = "a" * 100
        result = TextProcessor.truncate_text(long_text, 50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_extract_sentences_for_tts(self):
        text = "First sentence. Second sentence. Third sentence."
        chunks = TextProcessor.extract_sentences_for_tts(text, max_chars=30)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert len(chunk) <= 30 or chunk == text  # Allow single long sentence

class TestAudioPreprocessor:
    def setup_method(self):
        self.preprocessor = AudioPreprocessor()

    def test_process_returns_float32(self):
        audio = np.random.randn(16000).astype(np.int16)
        result = self.preprocessor.process(audio)
        assert result.dtype == np.float32

    def test_process_clamps_range(self):
        audio = np.random.randn(16000).astype(np.float32) * 2.0  # Overdriven
        result = self.preprocessor.process(audio)
        assert result.max() <= 1.0
        assert result.min() >= -1.0

    def test_process_empty_audio(self):
        audio = np.array([], dtype=np.float32)
        result = self.preprocessor.process(audio)
        assert len(result) == 0

    def test_dc_offset_removal(self):
        audio = np.ones(1000, dtype=np.float32) * 0.5
        result = self.preprocessor._remove_dc_offset(audio)
        assert abs(np.mean(result)) < 1e-6

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from translation.language_detector import LanguageDetector
from utils.text_utils import TextProcessor

class TestLanguageDetector:
    def setup_method(self):
        self.detector = LanguageDetector()

    def test_detect_heuristic_chinese(self):
        text = "你好世界这是中文文本"
        lang = self.detector._detect_heuristic(text)
        assert lang == 'zh'

    def test_detect_heuristic_arabic(self):
        text = "مرحبا بالعالم هذا نص عربي"
        lang = self.detector._detect_heuristic(text)
        assert lang == 'ar'

    def test_detect_heuristic_hindi(self):
        text = "नमस्ते दुनिया यह हिंदी पाठ है"
        lang = self.detector._detect_heuristic(text)
        assert lang == 'hi'

    def test_detect_heuristic_cyrillic(self):
        text = "Привет мир это русский текст"
        lang = self.detector._detect_heuristic(text)
        assert lang == 'ru'

    def test_detect_returns_none_for_empty(self):
        result = self.detector.detect("")
        assert result is None

    def test_detect_with_confidence_returns_tuple(self):
        lang, conf = self.detector.detect_with_confidence("Hello world, this is English text.")
        assert isinstance(conf, float)
        assert 0.0 <= conf <= 1.0

class TestNLLBLanguageMap:
    def test_nllb_has_common_languages(self):
        from translation.nllb import NLLB_LANGUAGE_MAP
        required = ['en', 'es', 'fr', 'de', 'zh', 'ar', 'hi', 'ru', 'ja', 'ko', 'pt']
        for lang in required:
            assert lang in NLLB_LANGUAGE_MAP, f"{lang} missing from NLLB map"

    def test_nllb_codes_format(self):
        from translation.nllb import NLLB_LANGUAGE_MAP
        for code, nllb_code in NLLB_LANGUAGE_MAP.items():
            parts = nllb_code.split('_')
            assert len(parts) == 2, f"Invalid NLLB code format: {nllb_code}"

class TestTranslationPipeline:
    @pytest.mark.asyncio
    async def test_same_language_passthrough(self):
        from translation.pipeline import TranslationPipeline
        from models.schemas import TranslationRequest
        nllb_mock = MagicMock()
        nllb_mock.is_loaded = False
        marian_mock = MagicMock()
        detector_mock = MagicMock()
        pipeline = TranslationPipeline(
            nllb=nllb_mock,
            marian=marian_mock,
            detector=detector_mock
        )
        req = TranslationRequest(
            text="Hello world",
            source_language="en",
            target_language="en"
        )
        result = await pipeline.translate(req)
        assert result.translated_text == "Hello world"
        assert result.model_used == "passthrough"
        assert result.confidence == 1.0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
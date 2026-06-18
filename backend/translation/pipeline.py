import logging
import time
import hashlib
from typing import Optional
from .nllb import NLLBTranslator
from .marian import MarianTranslator
from .language_detector import LanguageDetector
from models.schemas import TranslationResponse, TranslationRequest
from functools import lru_cache

logger = logging.getLogger(__name__)

_translation_cache: dict = {}  # simple LRU-style cache
_CACHE_MAX = 256

def _cache_key(text: str, src: str, tgt: str) -> str:
    return hashlib.md5(f"{src}|{tgt}|{text}".encode()).hexdigest()

class TranslationPipeline:
    """
    Unified translation pipeline with automatic model fallback.
    Priority: NLLB-200 → MarianMT → Error
    """

    def __init__(self, nllb: NLLBTranslator, marian: MarianTranslator, detector: LanguageDetector):
        self.nllb = nllb
        self.marian = marian
        self.detector = detector

    async def translate(self, request: TranslationRequest) -> TranslationResponse:
        """Translate text using best available model."""
        start_time = time.perf_counter()
        text = request.text.strip()
        source_lang = request.source_language
        target_lang = request.target_language

        if source_lang.lower()[:2] == target_lang.lower()[:2]:
            processing_time_ms = (time.perf_counter() - start_time) * 1000
            return TranslationResponse(translated_text=text, source_language=source_lang,
                target_language=target_lang, model_used="passthrough",
                confidence=1.0, processing_time_ms=processing_time_ms)

        # Auto-detect source language
        detected_lang = None
        if source_lang.lower() in ('auto', 'detect', ''):
            detected, conf = self.detector.detect_with_confidence(text)
            if detected:
                detected_lang = detected
                source_lang = detected
            else:
                source_lang = 'en'

        # Check cache
        cache_key = _cache_key(text, source_lang, target_lang)
        if cache_key in _translation_cache:
            cached = _translation_cache[cache_key]
            cached.processing_time_ms = (time.perf_counter() - start_time) * 1000
            return cached

        # Try NLLB-200 first
        if self.nllb is not None and self.nllb.is_loaded and self.nllb.supports_language(source_lang) and self.nllb.supports_language(target_lang):
            try:
                result = await self.nllb.translate(text, source_lang, target_lang)
                result.detected_language = detected_lang
                _store_cache(cache_key, result)
                return result
            except Exception as e:
                logger.warning(f"NLLB failed, trying Marian: {e}")

        # Marian fallback
        if self.marian is None:
            raise RuntimeError("No translation model available.")
        try:
            result = await self.marian.translate(text, source_lang, target_lang)
            if result:
                result.detected_language = detected_lang
                _store_cache(cache_key, result)
                return result
        except Exception as e:
            logger.error(f"Marian also failed: {e}")

        raise RuntimeError(f"All translation models failed for {source_lang} → {target_lang}.")

    def detect_language(self, text: str) -> Optional[str]:
        """Detect language of text."""
        return self.detector.detect(text)


def _store_cache(key: str, result: TranslationResponse) -> None:
    if len(_translation_cache) >= _CACHE_MAX:
        # evict oldest
        oldest = next(iter(_translation_cache))
        del _translation_cache[oldest]
    _translation_cache[key] = result

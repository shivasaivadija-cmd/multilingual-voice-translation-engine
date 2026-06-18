import logging
from typing import Optional, List, Tuple
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class LanguageDetector:
    """
    Language detection using lingua-py with fastText fallback.
    Returns ISO 639-1 language codes.
    """

    def __init__(self):
        self._lingua_detector = None
        self._fasttext_model = None
        self._using_lingua = False
        self._using_fasttext = False
        self._load_detectors()

    def _load_detectors(self) -> None:
        """Load language detectors in priority order."""
        # Try lingua-py first
        try:
            from lingua import LanguageDetectorBuilder, Language
            self._lingua_detector = (
                LanguageDetectorBuilder
                .from_all_languages()
                .build()  # lazy loading - no preload to avoid OOM
            )
            self._using_lingua = True
            logger.info("lingua-py language detector loaded.")
        except ImportError:
            logger.warning("lingua-py not available. Trying fastText.")

        # Try fastText as fallback
        if not self._using_lingua:
            try:
                import fasttext
                import os
                model_path = settings.FASTTEXT_MODEL_PATH
                if os.path.exists(model_path):
                    self._fasttext_model = fasttext.load_model(model_path)
                    self._using_fasttext = True
                    logger.info(f"fastText language detector loaded from {model_path}.")
                else:
                    logger.warning(f"fastText model not found at {model_path}.")
            except ImportError:
                logger.warning("fastText not available.")

        if not self._using_lingua and not self._using_fasttext:
            logger.warning("No language detector available. Will use whisper detected language.")

    def detect(self, text: str) -> Optional[str]:
        """Detect language of text. Returns ISO 639-1 code."""
        if not text or len(text.strip()) < 3:
            return None

        if self._using_lingua and self._lingua_detector:
            return self._detect_lingua(text)
        if self._using_fasttext and self._fasttext_model:
            return self._detect_fasttext(text)
        return self._detect_heuristic(text)

    def detect_with_confidence(self, text: str) -> Tuple[Optional[str], float]:
        """Detect language with confidence score."""
        if not text or len(text.strip()) < 3:
            return None, 0.0

        if self._using_lingua and self._lingua_detector:
            try:
                from lingua import Language
                confidence_values = self._lingua_detector.compute_language_confidence_values(text)
                if confidence_values:
                    best = confidence_values[0]
                    lang_code = self._lingua_to_iso(best.language)
                    return lang_code, float(best.value)
            except Exception as e:
                logger.warning(f"Lingua confidence detection failed: {e}")

        if self._using_fasttext and self._fasttext_model:
            lang, conf = self._detect_fasttext_with_conf(text)
            return lang, conf

        lang = self._detect_heuristic(text)
        return lang, 0.5 if lang else 0.0

    def _detect_lingua(self, text: str) -> Optional[str]:
        try:
            result = self._lingua_detector.detect_language_of(text)
            if result:
                return self._lingua_to_iso(result)
        except Exception as e:
            logger.warning(f"Lingua detection error: {e}")
        return None

    def _detect_fasttext(self, text: str) -> Optional[str]:
        lang, conf = self._detect_fasttext_with_conf(text)
        return lang

    def _detect_fasttext_with_conf(self, text: str) -> Tuple[Optional[str], float]:
        try:
            clean_text = text.replace('\n', ' ').strip()
            predictions = self._fasttext_model.predict(clean_text, k=1)
            if predictions and predictions[0]:
                label = predictions[0][0].replace('__label__', '')
                conf = float(predictions[1][0])
                return label, conf
        except Exception as e:
            logger.warning(f"fastText detection error: {e}")
        return None, 0.0

    def _detect_heuristic(self, text: str) -> Optional[str]:
        """Script-based heuristic fallback."""
        cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        if cjk / max(len(text), 1) > 0.2:
            return 'zh'
        arabic = sum(1 for c in text if '\u0600' <= c <= '\u06ff')
        if arabic / max(len(text), 1) > 0.2:
            return 'ar'
        devanagari = sum(1 for c in text if '\u0900' <= c <= '\u097f')
        if devanagari / max(len(text), 1) > 0.2:
            return 'hi'
        cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04ff')
        if cyrillic / max(len(text), 1) > 0.2:
            return 'ru'
        return 'en'

    def _lingua_to_iso(self, language) -> str:
        """Convert lingua Language enum to ISO 639-1 code."""
        mapping = {
            'ENGLISH': 'en', 'SPANISH': 'es', 'FRENCH': 'fr', 'GERMAN': 'de',
            'ITALIAN': 'it', 'PORTUGUESE': 'pt', 'RUSSIAN': 'ru', 'CHINESE': 'zh',
            'JAPANESE': 'ja', 'KOREAN': 'ko', 'ARABIC': 'ar', 'HINDI': 'hi',
            'TURKISH': 'tr', 'DUTCH': 'nl', 'POLISH': 'pl', 'SWEDISH': 'sv',
            'NORWEGIAN': 'no', 'DANISH': 'da', 'FINNISH': 'fi', 'CZECH': 'cs',
            'SLOVAK': 'sk', 'HUNGARIAN': 'hu', 'ROMANIAN': 'ro', 'BULGARIAN': 'bg',
            'CROATIAN': 'hr', 'SERBIAN': 'sr', 'UKRAINIAN': 'uk', 'GREEK': 'el',
            'HEBREW': 'he', 'THAI': 'th', 'VIETNAMESE': 'vi', 'INDONESIAN': 'id',
            'MALAY': 'ms', 'PERSIAN': 'fa', 'BENGALI': 'bn', 'TAMIL': 'ta',
            'URDU': 'ur', 'LATVIAN': 'lv', 'LITHUANIAN': 'lt', 'ESTONIAN': 'et',
            'SLOVENIAN': 'sl', 'ALBANIAN': 'sq', 'MACEDONIAN': 'mk', 'BASQUE': 'eu',
            'CATALAN': 'ca', 'GALICIAN': 'gl', 'WELSH': 'cy', 'IRISH': 'ga',
            'AFRIKAANS': 'af', 'SWAHILI': 'sw',
        }
        lang_name = str(language).split('.')[-1].upper()
        return mapping.get(lang_name, 'en')

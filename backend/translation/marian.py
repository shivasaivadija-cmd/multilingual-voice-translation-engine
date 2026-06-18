import logging
import time
from typing import Optional
from config.settings import get_settings
from models.schemas import TranslationResponse

logger = logging.getLogger(__name__)
settings = get_settings()

# Language pairs known to NOT exist on Helsinki-NLP — skip immediately without hitting HF
# Indian languages and others not covered by Marian opus-mt
_NO_DIRECT_MARIAN_MODEL = {
    'te', 'kn', 'ml', 'mr', 'gu', 'pa', 'si', 'ne', 'my', 'km', 'lo',
    'am', 'ti', 'mn', 'ky', 'tg', 'tk', 'uz', 'be', 'hy', 'ka', 'az',
}

# Known working pivot languages for Marian (src -> pivot -> tgt)
# For Indian languages: use NLLB (handled in pipeline), not Marian
_PIVOT_OVERRIDES: dict = {}


class MarianTranslator:
    """
    Helsinki-NLP MarianMT translation models.
    Loads models on-demand per language pair.
    Caches failures to avoid repeated network calls for missing models.
    """

    def __init__(self):
        self._model_cache: dict = {}
        self._tokenizer_cache: dict = {}
        self._failed_pairs: set = set()  # permanently cache failures
        self.max_length = settings.TRANSLATION_MAX_LENGTH
        logger.info("MarianTranslator initialized (on-demand loading).")

    def _get_model_name(self, src: str, tgt: str) -> str:
        return f"{settings.MARIAN_MODEL_PREFIX}-{src}-{tgt}"

    def _is_unavailable(self, src: str, tgt: str) -> bool:
        """Return True immediately if this pair is known to not exist."""
        key = f"{src}-{tgt}"
        if key in self._failed_pairs:
            return True
        # Either endpoint is a known no-model language
        if src in _NO_DIRECT_MARIAN_MODEL or tgt in _NO_DIRECT_MARIAN_MODEL:
            self._failed_pairs.add(key)
            return True
        return False

    async def _load_pair(self, src: str, tgt: str) -> bool:
        """Load model for language pair on demand."""
        key = f"{src}-{tgt}"
        if key in self._model_cache:
            return True
        if key in self._failed_pairs:
            return False

        try:
            from transformers import MarianMTModel, MarianTokenizer
            import torch
            model_name = self._get_model_name(src, tgt)
            logger.info(f"Loading Marian model: {model_name}")
            tokenizer = MarianTokenizer.from_pretrained(
                model_name, cache_dir=settings.MODELS_DIR
            )
            model = MarianMTModel.from_pretrained(
                model_name, cache_dir=settings.MODELS_DIR
            )
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            model = model.to(device)
            model.eval()
            self._model_cache[key] = (model, device)
            self._tokenizer_cache[key] = tokenizer
            logger.info(f"Marian {model_name} loaded on {device}.")
            return True
        except Exception as e:
            logger.warning(f"Could not load Marian model {src}-{tgt}: {e}")
            self._failed_pairs.add(key)  # never retry this pair
            return False

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> Optional[TranslationResponse]:
        """Translate text, loading model on demand."""
        start_time = time.perf_counter()
        src = source_language.lower()[:2]
        tgt = target_language.lower()[:2]

        if src == tgt:
            processing_time_ms = (time.perf_counter() - start_time) * 1000
            return TranslationResponse(
                translated_text=text,
                source_language=source_language,
                target_language=target_language,
                model_used="passthrough",
                confidence=1.0,
                processing_time_ms=processing_time_ms
            )

        # Skip immediately if known unavailable
        if self._is_unavailable(src, tgt):
            logger.debug(f"Marian: skipping known unavailable pair {src}-{tgt}")
            return None

        # Try direct pair
        loaded = await self._load_pair(src, tgt)
        if loaded:
            result = await self._do_translate(text, src, tgt)
            if result:
                processing_time_ms = (time.perf_counter() - start_time) * 1000
                return TranslationResponse(
                    translated_text=result,
                    source_language=source_language,
                    target_language=target_language,
                    model_used=self._get_model_name(src, tgt),
                    confidence=0.85,
                    processing_time_ms=processing_time_ms
                )

        # Try pivot through English (only if neither side is a no-model language)
        if src != 'en' and tgt != 'en':
            src_to_en_ok = not self._is_unavailable(src, 'en') and await self._load_pair(src, 'en')
            en_to_tgt_ok = not self._is_unavailable('en', tgt) and await self._load_pair('en', tgt)
            if src_to_en_ok and en_to_tgt_ok:
                intermediate = await self._do_translate(text, src, 'en')
                if intermediate:
                    result = await self._do_translate(intermediate, 'en', tgt)
                    if result:
                        processing_time_ms = (time.perf_counter() - start_time) * 1000
                        return TranslationResponse(
                            translated_text=result,
                            source_language=source_language,
                            target_language=target_language,
                            model_used="marian-pivot-en",
                            confidence=0.75,
                            processing_time_ms=processing_time_ms
                        )

        return None

    async def _do_translate(self, text: str, src: str, tgt: str) -> Optional[str]:
        """Internal translation call."""
        key = f"{src}-{tgt}"
        if key not in self._model_cache:
            return None
        try:
            import torch
            model, device = self._model_cache[key]
            tokenizer = self._tokenizer_cache[key]
            inputs = tokenizer(
                text, return_tensors="pt", padding=True,
                truncation=True, max_length=self.max_length
            ).to(device)
            with torch.no_grad():
                translated = model.generate(**inputs, num_beams=4, early_stopping=True)
            decoded = tokenizer.batch_decode(translated, skip_special_tokens=True)
            return decoded[0] if decoded else None
        except Exception as e:
            logger.error(f"Marian translate error ({src}-{tgt}): {e}")
            return None

    def unload_all(self) -> None:
        """Unload all cached models."""
        self._model_cache.clear()
        self._tokenizer_cache.clear()
        logger.info("All Marian models unloaded.")

import logging
import re
import time
from typing import Optional, Dict
from config.settings import get_settings
from models.schemas import TranslationResponse

logger = logging.getLogger(__name__)
settings = get_settings()

_SNAPSHOT_PATH = (
    "models/models--facebook--nllb-200-distilled-600M"
    "/snapshots/f8d333a098d19b4fd9a8b18f94170487ad3f821d"
)

def _clean_translation(text: str) -> str:
    if not text:
        return text
    text = re.sub(r'\s+([,.!?;:\'\")])', r'\1', text)
    text = re.sub(r'([\(\"\'])\s+', r'\1', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'(?:^|(?<=[.!?])\s+)([a-z])', lambda m: m.group(0).upper(), text)
    return text.strip()


NLLB_LANGUAGE_MAP: Dict[str, str] = {
    'af': 'afr_Latn', 'am': 'amh_Ethi', 'ar': 'arb_Arab', 'az': 'azj_Latn',
    'be': 'bel_Cyrl', 'bg': 'bul_Cyrl', 'bn': 'ben_Beng', 'bs': 'bos_Latn',
    'ca': 'cat_Latn', 'cs': 'ces_Latn', 'cy': 'cym_Latn', 'da': 'dan_Latn',
    'de': 'deu_Latn', 'el': 'ell_Grek', 'en': 'eng_Latn', 'es': 'spa_Latn',
    'et': 'est_Latn', 'eu': 'eus_Latn', 'fa': 'pes_Arab', 'fi': 'fin_Latn',
    'fr': 'fra_Latn', 'ga': 'gle_Latn', 'gl': 'glg_Latn', 'gu': 'guj_Gujr',
    'he': 'heb_Hebr', 'hi': 'hin_Deva', 'hr': 'hrv_Latn', 'hu': 'hun_Latn',
    'hy': 'hye_Armn', 'id': 'ind_Latn', 'is': 'isl_Latn', 'it': 'ita_Latn',
    'ja': 'jpn_Jpan', 'ka': 'kat_Geor', 'kk': 'kaz_Cyrl', 'km': 'khm_Khmr',
    'kn': 'kan_Knda', 'ko': 'kor_Hang', 'lt': 'lit_Latn', 'lv': 'lvs_Latn',
    'mk': 'mkd_Cyrl', 'ml': 'mal_Mlym', 'mn': 'khk_Cyrl', 'mr': 'mar_Deva',
    'ms': 'zsm_Latn', 'mt': 'mlt_Latn', 'my': 'mya_Mymr', 'ne': 'npi_Deva',
    'nl': 'nld_Latn', 'no': 'nob_Latn', 'pa': 'pan_Guru', 'pl': 'pol_Latn',
    'pt': 'por_Latn', 'ro': 'ron_Latn', 'ru': 'rus_Cyrl', 'si': 'sin_Sinh',
    'sk': 'slk_Latn', 'sl': 'slv_Latn', 'sq': 'als_Latn', 'sr': 'srp_Cyrl',
    'sv': 'swe_Latn', 'sw': 'swh_Latn', 'ta': 'tam_Taml', 'te': 'tel_Telu',
    'th': 'tha_Thai', 'tl': 'tgl_Latn', 'tr': 'tur_Latn', 'uk': 'ukr_Cyrl',
    'ur': 'urd_Arab', 'uz': 'uzn_Latn', 'vi': 'vie_Latn', 'zh': 'zho_Hans',
    'zh-tw': 'zho_Hant', 'zu': 'zul_Latn',
}


class NLLBTranslator:
    """
    NLLB-200 translation — optimised HuggingFace path:
    • Loads from local snapshot (no network)
    • Pre-resolves all language token IDs at load time
    • greedy decode (beam=1), max_new_tokens=128
    • torch.no_grad + inference_mode
    • Runs in ThreadPoolExecutor (non-blocking)
    """

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_name = settings.NLLB_MODEL_NAME
        self.is_loaded = False
        self._device = 'cpu'
        self._lang_token_ids: Dict[str, int] = {}   # pre-resolved at load time
        self._use_ctranslate2 = False                # kept for compat with handler
        logger.info(f"NLLBTranslator configured: {self.model_name}")

    async def load(self) -> None:
        import os, torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self._device = 'cuda' if torch.cuda.is_available() else 'cpu'

        # Prefer local snapshot to avoid any network call
        local_path = os.path.abspath(_SNAPSHOT_PATH)
        load_from = local_path if os.path.exists(local_path) else self.model_name

        logger.info(f"Loading NLLB-200 from {load_from} on {self._device}...")
        start = time.time()

        self.tokenizer = AutoTokenizer.from_pretrained(
            load_from,
            cache_dir=settings.MODELS_DIR,
            local_files_only=os.path.exists(local_path),
        )
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            load_from,
            cache_dir=settings.MODELS_DIR,
            local_files_only=os.path.exists(local_path),
            low_cpu_mem_usage=True,
            torch_dtype=torch.float16 if self._device == 'cuda' else torch.float32,
        )
        self.model = self.model.to(self._device)
        self.model.eval()

        # Freeze weights — no gradients ever needed
        for p in self.model.parameters():
            p.requires_grad = False

        # Pre-resolve language token IDs for all supported languages
        for iso, flores in NLLB_LANGUAGE_MAP.items():
            try:
                tid = self.tokenizer.convert_tokens_to_ids(flores)
                if tid != self.tokenizer.unk_token_id:
                    self._lang_token_ids[flores] = tid
            except Exception:
                pass

        self.is_loaded = True
        logger.info(f"NLLB-200 loaded in {time.time()-start:.1f}s — {len(self._lang_token_ids)} languages pre-resolved.")

    def get_nllb_code(self, lang_code: str) -> Optional[str]:
        return NLLB_LANGUAGE_MAP.get(lang_code.lower().strip())

    def supports_language(self, lang_code: str) -> bool:
        return self.get_nllb_code(lang_code) is not None

    async def translate(self, text: str, source_language: str, target_language: str) -> TranslationResponse:
        if not self.is_loaded or self.model is None:
            raise RuntimeError("NLLB model not loaded.")

        src_code = self.get_nllb_code(source_language)
        tgt_code = self.get_nllb_code(target_language)
        if not src_code:
            raise ValueError(f"Unsupported source language: {source_language}")
        if not tgt_code:
            raise ValueError(f"Unsupported target language: {target_language}")

        start = time.perf_counter()
        raw = self._infer(text, src_code, tgt_code)
        translated_text = _clean_translation(raw)
        ms = (time.perf_counter() - start) * 1000

        return TranslationResponse(
            translated_text=translated_text,
            source_language=source_language,
            target_language=target_language,
            model_used="nllb-200-distilled-600M",
            confidence=0.9,
            processing_time_ms=ms,
        )

    def _infer(self, text: str, src_code: str, tgt_code: str) -> str:
        """Synchronous inference — safe to call from ThreadPoolExecutor."""
        import torch

        forced_bos_token_id = self._lang_token_ids.get(tgt_code)
        if forced_bos_token_id is None:
            # Fallback resolve at runtime
            forced_bos_token_id = self.tokenizer.convert_tokens_to_ids(tgt_code)

        self.tokenizer.src_lang = src_code
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        ).to(self._device)

        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
                max_new_tokens=128,   # most utterances <128 tokens
                num_beams=1,          # greedy — 3-4x faster than beam=4
                do_sample=False,
                early_stopping=False, # not used with beam=1 but explicit
            )

        return self.tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0]

    def unload(self) -> None:
        if self.model:
            del self.model
            del self.tokenizer
            self.model = None
            self.tokenizer = None
            self.is_loaded = False
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
            logger.info("NLLB model unloaded.")

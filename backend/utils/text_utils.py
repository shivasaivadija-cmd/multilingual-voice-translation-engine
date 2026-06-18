import re
import unicodedata
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class TextProcessor:
    """Text processing utilities."""

    # Patterns to preserve in translation
    PRESERVE_PATTERNS = [
        r'\b\d{1,4}[-./]\d{1,2}[-./]\d{1,4}\b',  # Dates
        r'\b\+?\d[\d\s\-().]{7,}\d\b',            # Phone numbers
        r'\b[A-Z]{2,}\b',                           # Abbreviations
        r'\b\d+\.?\d*\s*(?:kg|lb|km|mi|mph|kph|°C|°F|USD|EUR|GBP)\b',  # Units
        r'https?://[^\s]+',                          # URLs
        r'[\U0001F600-\U0001FFFF]',                 # Emojis
    ]

    @staticmethod
    def clean_transcript(text: str) -> str:
        """Clean whisper transcript output."""
        if not text:
            return ""
        # Remove leading/trailing whitespace
        text = text.strip()
        # Fix multiple spaces
        text = re.sub(r'  +', ' ', text)
        # Remove whisper artifacts
        text = re.sub(r'\[BLANK_AUDIO\]', '', text)
        text = re.sub(r'\(Music\)', '', text, flags=re.IGNORECASE)
        # Fix punctuation spacing
        text = re.sub(r'\s([.,!?;:])', r'\1', text)
        return text.strip()

    @staticmethod
    def restore_punctuation(text: str) -> str:
        """Basic punctuation restoration heuristics."""
        if not text:
            return text
        # Capitalize first letter
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        # Add period if no sentence-ending punctuation
        if text and text[-1] not in '.!?':
            text = text + '.'
        return text

    @staticmethod
    def split_into_sentences(text: str) -> List[str]:
        """Split text into sentences."""
        pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\s*$'
        sentences = re.split(pattern, text.strip())
        return [s.strip() for s in sentences if s.strip()]

    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
        """Truncate text to max length."""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)].rstrip() + suffix

    @staticmethod
    def detect_language_hints(text: str) -> Optional[str]:
        """Simple script-based language hint detection."""
        # Check for CJK characters
        cjk_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        if cjk_count / max(len(text), 1) > 0.3:
            return "zh"
        # Check for Arabic
        arabic_count = sum(1 for c in text if '\u0600' <= c <= '\u06ff')
        if arabic_count / max(len(text), 1) > 0.3:
            return "ar"
        # Check for Devanagari
        deva_count = sum(1 for c in text if '\u0900' <= c <= '\u097f')
        if deva_count / max(len(text), 1) > 0.3:
            return "hi"
        # Check for Cyrillic
        cyrillic_count = sum(1 for c in text if '\u0400' <= c <= '\u04ff')
        if cyrillic_count / max(len(text), 1) > 0.3:
            return "ru"
        return None

    @staticmethod
    def normalize_unicode(text: str) -> str:
        """Normalize unicode text."""
        return unicodedata.normalize('NFC', text)

    @staticmethod
    def remove_special_chars(text: str, keep_punctuation: bool = True) -> str:
        """Remove special characters while preserving meaning."""
        if keep_punctuation:
            pattern = r'[^\w\s.,!?;:\-\'"]'
        else:
            pattern = r'[^\w\s]'
        return re.sub(pattern, '', text)

    @staticmethod
    def count_words(text: str) -> int:
        """Count words in text."""
        return len(text.split())

    @staticmethod
    def extract_sentences_for_tts(text: str, max_chars: int = 200) -> List[str]:
        """Extract sentences optimized for TTS streaming."""
        sentences = TextProcessor.split_into_sentences(text)
        chunks = []
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_chars:
                current_chunk = (current_chunk + " " + sentence).strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
        if current_chunk:
            chunks.append(current_chunk)
        return chunks if chunks else [text]

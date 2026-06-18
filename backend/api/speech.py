import logging
from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
from models.schemas import TranscriptionRequest, TranscriptionResponse
from database.connection import get_session
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    request: Request,
    audio: UploadFile = File(..., description="Audio file (WAV, MP3, M4A, OGG, FLAC)"),
    language: Optional[str] = Form(None),
    beam_size: int = Form(5),
    vad_filter: bool = Form(True),
    word_timestamps: bool = Form(True),
    db: AsyncSession = Depends(get_session),
):
    """Transcribe audio file using Whisper."""
    # Validate file type
    allowed_types = {
        'audio/wav', 'audio/wave', 'audio/mpeg', 'audio/mp3',
        'audio/mp4', 'audio/m4a', 'audio/ogg', 'audio/flac',
        'audio/webm', 'video/webm'
    }
    if audio.content_type and audio.content_type not in allowed_types:
        if not audio.filename.lower().endswith((".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm")):
            raise HTTPException(status_code=400, detail=f"Unsupported audio type: {audio.content_type}")

    try:
        audio_bytes = await audio.read()
        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file.")
        if len(audio_bytes) > 100 * 1024 * 1024:  # 100MB limit
            raise HTTPException(status_code=413, detail="Audio file too large (max 100MB).")

        model_manager = request.app.state.model_manager
        if not model_manager.whisper or not model_manager.whisper.is_loaded:
            raise HTTPException(status_code=503, detail="Speech recognition model not ready.")

        params = TranscriptionRequest(
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            word_timestamps=word_timestamps,
        )

        result = await model_manager.speech_pipeline.process_audio_bytes(
            audio_bytes=audio_bytes,
            language=language,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@router.get("/languages")
async def list_supported_languages():
    """Get list of all languages supported by ASR."""
    return {
        "languages": WHISPER_SUPPORTED_LANGUAGES,
        "total": len(WHISPER_SUPPORTED_LANGUAGES)
    }

WHISPER_SUPPORTED_LANGUAGES = [
    {"code": "auto", "name": "Auto Detect"},
    {"code": "af", "name": "Afrikaans"}, {"code": "ar", "name": "Arabic"},
    {"code": "az", "name": "Azerbaijani"}, {"code": "be", "name": "Belarusian"},
    {"code": "bg", "name": "Bulgarian"}, {"code": "bn", "name": "Bengali"},
    {"code": "bs", "name": "Bosnian"}, {"code": "ca", "name": "Catalan"},
    {"code": "cs", "name": "Czech"}, {"code": "cy", "name": "Welsh"},
    {"code": "da", "name": "Danish"}, {"code": "de", "name": "German"},
    {"code": "el", "name": "Greek"}, {"code": "en", "name": "English"},
    {"code": "es", "name": "Spanish"}, {"code": "et", "name": "Estonian"},
    {"code": "eu", "name": "Basque"}, {"code": "fa", "name": "Persian"},
    {"code": "fi", "name": "Finnish"}, {"code": "fr", "name": "French"},
    {"code": "gl", "name": "Galician"}, {"code": "gu", "name": "Gujarati"},
    {"code": "he", "name": "Hebrew"}, {"code": "hi", "name": "Hindi"},
    {"code": "hr", "name": "Croatian"}, {"code": "hu", "name": "Hungarian"},
    {"code": "hy", "name": "Armenian"}, {"code": "id", "name": "Indonesian"},
    {"code": "is", "name": "Icelandic"}, {"code": "it", "name": "Italian"},
    {"code": "ja", "name": "Japanese"}, {"code": "ka", "name": "Georgian"},
    {"code": "kk", "name": "Kazakh"}, {"code": "km", "name": "Khmer"},
    {"code": "kn", "name": "Kannada"}, {"code": "ko", "name": "Korean"},
    {"code": "lt", "name": "Lithuanian"}, {"code": "lv", "name": "Latvian"},
    {"code": "mk", "name": "Macedonian"}, {"code": "ml", "name": "Malayalam"},
    {"code": "mn", "name": "Mongolian"}, {"code": "mr", "name": "Marathi"},
    {"code": "ms", "name": "Malay"}, {"code": "mt", "name": "Maltese"},
    {"code": "my", "name": "Burmese"}, {"code": "ne", "name": "Nepali"},
    {"code": "nl", "name": "Dutch"}, {"code": "no", "name": "Norwegian"},
    {"code": "pa", "name": "Punjabi"}, {"code": "pl", "name": "Polish"},
    {"code": "pt", "name": "Portuguese"}, {"code": "ro", "name": "Romanian"},
    {"code": "ru", "name": "Russian"}, {"code": "si", "name": "Sinhala"},
    {"code": "sk", "name": "Slovak"}, {"code": "sl", "name": "Slovenian"},
    {"code": "sq", "name": "Albanian"}, {"code": "sr", "name": "Serbian"},
    {"code": "sv", "name": "Swedish"}, {"code": "sw", "name": "Swahili"},
    {"code": "ta", "name": "Tamil"}, {"code": "te", "name": "Telugu"},
    {"code": "th", "name": "Thai"}, {"code": "tl", "name": "Filipino"},
    {"code": "tr", "name": "Turkish"}, {"code": "uk", "name": "Ukrainian"},
    {"code": "ur", "name": "Urdu"}, {"code": "uz", "name": "Uzbek"},
    {"code": "vi", "name": "Vietnamese"}, {"code": "zh", "name": "Chinese"},
    {"code": "zu", "name": "Zulu"},
]
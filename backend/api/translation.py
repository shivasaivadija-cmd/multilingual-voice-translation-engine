import logging
import asyncio
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from models.schemas import TranslationRequest, TranslationResponse, TextTranslateRequest, TextTranslateResponse
from database.connection import get_session
from services.history_service import HistoryService

logger = logging.getLogger(__name__)
router = APIRouter()
_history_service = HistoryService()

# Chunk size: translate in 2000-char paragraphs to stay within model limits
_CHUNK_SIZE = 2000

def _split_chunks(text: str, size: int = _CHUNK_SIZE) -> list[str]:
    """Split text by double-newline paragraphs; fall back to hard split."""
    paragraphs = text.split('\n\n')
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= size:
            current = (current + '\n\n' + para).lstrip('\n')
        else:
            if current:
                chunks.append(current)
            # para itself might exceed size – hard split
            while len(para) > size:
                chunks.append(para[:size])
                para = para[size:]
            current = para
    if current:
        chunks.append(current)
    return chunks or [text]

@router.post("/translate", response_model=TranslationResponse)
async def translate_text(
    request: Request,
    body: TranslationRequest,
    db: AsyncSession = Depends(get_session)
):
    """Translate text from source to target language."""
    try:
        model_manager = request.app.state.model_manager
        if not model_manager.translation_pipeline:
            raise HTTPException(status_code=503, detail="Translation model not ready.")
        result = await model_manager.translation_pipeline.translate(body)
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Translation endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

@router.post("/translate-text", response_model=TextTranslateResponse)
async def translate_large_text(
    request: Request,
    body: TextTranslateRequest,
    db: AsyncSession = Depends(get_session)
):
    """Translate large text with chunking. Saves result to history."""
    try:
        model_manager = request.app.state.model_manager
        if not model_manager.translation_pipeline:
            raise HTTPException(status_code=503, detail="Translation model not ready.")

        import time
        start = time.perf_counter()
        chunks = _split_chunks(body.text)

        from models.schemas import TranslationRequest
        translated_chunks = []
        detected_lang = None
        model_used = "unknown"
        total_confidence = 0.0

        for chunk in chunks:
            req = TranslationRequest(
                text=chunk,
                source_language=body.source_language,
                target_language=body.target_language,
                preserve_formatting=True,
            )
            res = await model_manager.translation_pipeline.translate(req)
            translated_chunks.append(res.translated_text)
            if not detected_lang and res.detected_language:
                detected_lang = res.detected_language
            model_used = res.model_used
            total_confidence += res.confidence

        translated_text = '\n\n'.join(translated_chunks)
        processing_time_ms = (time.perf_counter() - start) * 1000
        avg_confidence = total_confidence / len(chunks)

        if body.save_history:
            try:
                await _history_service.save_entry(
                    db=db,
                    original_text=body.text[:1000],
                    translated_text=translated_text[:1000],
                    source_language=detected_lang or body.source_language,
                    target_language=body.target_language,
                    confidence=avg_confidence,
                )
            except Exception as he:
                logger.warning(f"Failed to save text translation to history: {he}")

        return TextTranslateResponse(
            translated_text=translated_text,
            source_language=detected_lang or body.source_language,
            target_language=body.target_language,
            detected_language=detected_lang,
            model_used=model_used,
            confidence=avg_confidence,
            processing_time_ms=processing_time_ms,
            char_count=len(body.text),
            chunk_count=len(chunks),
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Text translation endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

@router.post("/detect-language")
async def detect_language(request: Request, body: dict):
    """Detect language of text."""
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Text is required.")
    model_manager = request.app.state.model_manager
    if not model_manager.lang_detector:
        raise HTTPException(status_code=503, detail="Language detector not ready.")
    lang, confidence = model_manager.lang_detector.detect_with_confidence(text)
    return {"language": lang, "confidence": confidence}
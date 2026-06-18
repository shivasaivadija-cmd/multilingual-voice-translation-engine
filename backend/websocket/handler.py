import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from models.schemas import TTSRequest
import numpy as np

logger = logging.getLogger(__name__)
router = APIRouter()

# Thread pool for CPU-bound inference - 3 workers for parallel processing!
_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="inference")

# Tuning constants
SAMPLE_RATE = 16000
VAD_SPEECH_THRESHOLD = 0.50
VAD_SILENCE_THRESHOLD = 0.30
SILENCE_TO_COMMIT_S = 0.6      # was 1.0 — commit faster after speech ends
MIN_SPEECH_S = 0.25            # reduced from 0.3 - ultra-responsive!
MAX_UTTERANCE_S = 45.0
MIN_ENERGY = 0.002
VAD_SEND_INTERVAL = 0.10   # throttle VAD WebSocket messages to max 10/sec
PARTIAL_INTERVAL_S = 0.3   # reduced from 0.4 - SUPER FAST partials!
MIN_PARTIAL_AUDIO_S = 0.3  # minimum audio needed before first partial - INSTANT!


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_states: Dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_states[session_id] = self._fresh_state()
        logger.info(f"WebSocket connected: {session_id}")

    def _fresh_state(self) -> dict:
        return {
            "source_language": None,
            "target_language": "en",
            "is_listening": False,
            "speech_buffer": [],
            "speech_duration": 0.0,
            "silence_duration": 0.0,
            "in_speech": False,
            "sequence": 0,
            "last_vad_send": 0.0,   # timestamp of last VAD message sent
            "last_partial_send": 0.0,  # timestamp of last partial transcription
            "partial_sent": False,     # track if we sent a partial for this utterance
        }

    def disconnect(self, session_id: str) -> None:
        self.active_connections.pop(session_id, None)
        self.session_states.pop(session_id, None)
        logger.info(f"WebSocket disconnected: {session_id}")

    async def send_json(self, session_id: str, data: dict) -> bool:
        ws = self.active_connections.get(session_id)
        if ws and ws.client_state == WebSocketState.CONNECTED:
            try:
                await ws.send_json(data)
                return True
            except Exception as e:
                logger.warning(f"Send failed [{session_id}]: {e}")
        return False


manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    app = websocket.app
    model_manager = app.state.model_manager

    await manager.connect(websocket, session_id)
    await manager.send_json(session_id, {
        "type": "connected",
        "session_id": session_id,
        "status": model_manager.get_status()["models_loaded"]
    })

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive(), timeout=60.0)
            except asyncio.TimeoutError:
                await manager.send_json(session_id, {"type": "ping"})
                continue

            if data["type"] == "websocket.disconnect":
                break

            if "text" in data:
                await _handle_text(session_id, data["text"], model_manager)
            elif "bytes" in data:
                await _handle_audio(session_id, data["bytes"], model_manager)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS error [{session_id}]: {e}", exc_info=True)
        await manager.send_json(session_id, {"type": "error", "message": str(e)})
    finally:
        manager.disconnect(session_id)


async def _handle_text(session_id: str, raw: str, model_manager) -> None:
    try:
        msg = json.loads(raw)
        msg_type = msg.get("type", "")
        state = manager.session_states.get(session_id, {})

        if msg_type == "config":
            if "source_language" in msg:
                state["source_language"] = msg["source_language"] or None
            if "target_language" in msg:
                state["target_language"] = msg["target_language"]
            await manager.send_json(session_id, {"type": "config_ack"})

        elif msg_type == "start_listening":
            # Reset utterance state
            state.update({
                "is_listening": True,
                "speech_buffer": [],
                "speech_duration": 0.0,
                "silence_duration": 0.0,
                "in_speech": False,
            })
            if model_manager.vad:
                model_manager.vad.reset()
            await manager.send_json(session_id, {"type": "listening_started"})

        elif msg_type == "stop_listening":
            state["is_listening"] = False
            # Commit any remaining buffered speech
            if state.get("speech_buffer") and state.get("speech_duration", 0) >= MIN_SPEECH_S:
                await _commit_utterance(session_id, state, model_manager)
            state.update({"speech_buffer": [], "speech_duration": 0.0,
                          "silence_duration": 0.0, "in_speech": False})
            await manager.send_json(session_id, {"type": "listening_stopped"})

        elif msg_type == "ping":
            await manager.send_json(session_id, {"type": "pong", "timestamp": time.time()})

        elif msg_type == "retranslate":
            text = msg.get("text", "").strip()
            src = msg.get("source_language") or state.get("source_language") or "en"
            tgt = msg.get("target_language") or state.get("target_language") or "en"
            if text and model_manager.translation_pipeline:
                try:
                    loop = asyncio.get_event_loop()
                    translated = await _translate_long(text, src, tgt,
                                                       model_manager.translation_pipeline, loop)
                    await manager.send_json(session_id, {
                        "type": "retranslation",
                        "translation": translated,
                        "target_language": tgt,
                    })
                except Exception as e:
                    logger.warning(f"Retranslate failed: {e}")
                    await manager.send_json(session_id, {
                        "type": "retranslation",
                        "translation": text,
                        "target_language": tgt,
                    })

    except json.JSONDecodeError:
        await manager.send_json(session_id, {"type": "error", "message": "Invalid JSON."})
    except Exception as e:
        logger.error(f"Text handler error: {e}", exc_info=True)


async def _handle_audio(session_id: str, audio_bytes: bytes, model_manager) -> None:
    state = manager.session_states.get(session_id)
    if not state or not state.get("is_listening"):
        return
    if not model_manager.whisper or not model_manager.whisper.is_loaded:
        return

    # Convert to float32 PCM
    chunk = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    chunk_duration = len(chunk) / SAMPLE_RATE

    # Energy gate — skip frames that are essentially silent (below noise floor)
    energy = float(np.sqrt(np.mean(chunk ** 2)))
    if energy < MIN_ENERGY:
        vad_prob = 0.0
    else:
        # VAD check
        vad_prob = model_manager.vad.is_speech(chunk) if model_manager.vad else 0.5

    is_speech = vad_prob >= VAD_SPEECH_THRESHOLD
    is_silence = vad_prob < VAD_SILENCE_THRESHOLD

    # Send VAD status — throttled to VAD_SEND_INTERVAL to avoid flooding WS
    now = time.monotonic()
    if now - state.get("last_vad_send", 0.0) >= VAD_SEND_INTERVAL:
        state["last_vad_send"] = now
        await manager.send_json(session_id, {
            "type": "vad",
            "speech_probability": round(vad_prob, 3),
            "is_speech": is_speech,
        })

    if is_speech:
        # Accumulate speech frames
        state["speech_buffer"].append(chunk)
        state["speech_duration"] += chunk_duration
        state["silence_duration"] = 0.0
        state["in_speech"] = True

        # Partials disabled — final result is accurate and fast enough

        # Force-commit if utterance is too long
        if state["speech_duration"] >= MAX_UTTERANCE_S:
            await _commit_utterance(session_id, state, model_manager)
            state.update({"speech_buffer": [], "speech_duration": 0.0,
                          "silence_duration": 0.0, "in_speech": True, 
                          "partial_sent": False})

    elif state.get("in_speech"):
        # We were in speech, now silence — track silence duration
        state["silence_duration"] += chunk_duration

        if state["silence_duration"] >= SILENCE_TO_COMMIT_S:
            # Enough silence → utterance is complete
            if state["speech_duration"] >= MIN_SPEECH_S:
                await _commit_utterance(session_id, state, model_manager)
            # Reset for next utterance
            state.update({"speech_buffer": [], "speech_duration": 0.0,
                          "silence_duration": 0.0, "in_speech": False,
                          "partial_sent": False})
            if model_manager.vad:
                model_manager.vad.reset()
    # else: silence before any speech started — just ignore


async def _send_partial_transcript(session_id: str, state: dict, model_manager) -> None:
    """Send INSTANT partial transcription while user is speaking."""
    if not state.get("speech_buffer") or state["speech_duration"] < MIN_PARTIAL_AUDIO_S:
        return
    
    state["partial_sent"] = True
    
    # OPTIMIZATION: Only use last 1.5 seconds of audio for partials (super fast!)
    max_partial_duration = 1.5  # seconds
    buffer_copy = state["speech_buffer"].copy()
    
    # Calculate how many chunks to skip from beginning
    total_samples = sum(len(chunk) for chunk in buffer_copy)
    max_samples = int(max_partial_duration * SAMPLE_RATE)
    
    if total_samples > max_samples:
        # Take only the last 1.5s
        samples_to_take = max_samples
        chunks_to_use = []
        samples_accumulated = 0
        for chunk in reversed(buffer_copy):
            chunks_to_use.insert(0, chunk)
            samples_accumulated += len(chunk)
            if samples_accumulated >= samples_to_take:
                break
        audio = np.concatenate(chunks_to_use)
    else:
        audio = np.concatenate(buffer_copy)
    
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            _run_whisper_partial,
            model_manager.whisper.model,
            audio,
            state.get("source_language"),
        )
        text = result[0].strip() if result[0] else ""
        if text and len(text) > 2 and not _is_hallucination(text):
            await manager.send_json(session_id, {
                "type": "transcription",
                "text": text,
                "is_partial": True,
                "confidence": 0.6,
                "language": result[1],
            })
    except Exception as e:
        logger.debug(f"Partial transcript error: {e}")


def _run_whisper_partial(model, audio: np.ndarray, language):
    """INSTANT partial transcription - absolute minimum processing."""
    # Ultra-minimal settings for real-time speed
    segments, info = model.transcribe(
        audio,
        language=language,
        beam_size=1,  # greedy
        word_timestamps=False,
        vad_filter=False,
        temperature=0.0,
        condition_on_previous_text=False,
        without_timestamps=True,
        best_of=1,
        log_prob_threshold=None,  # skip log prob calculation
        no_speech_threshold=0.8,  # higher - skip processing non-speech faster
    )
    text = "".join(seg.text for seg in segments)
    return text, info.language


async def _commit_utterance(session_id: str, state: dict, model_manager) -> None:
    """Transcribe accumulated speech buffer and translate."""
    if not state.get("speech_buffer"):
        return

    audio = np.concatenate(state["speech_buffer"])
    try:
        loop = asyncio.get_event_loop()

        # Run Whisper synchronously in thread pool — model.transcribe() is sync under the hood
        result = await loop.run_in_executor(
            _executor,
            _run_whisper_sync,
            model_manager.whisper.model,
            audio,
            state.get("source_language"),
        )

        text = result[0].strip() if result[0] else ""
        detected_lang = result[1]

        if not text:
            await manager.send_json(session_id, {"type": "no_speech", "reason": "unclear"})
            return

        if _is_hallucination(text):
            logger.debug(f"Filtered hallucination: '{text}'")
            await manager.send_json(session_id, {"type": "no_speech", "reason": "noise"})
            return

        seq = state.get("sequence", 0)
        state["sequence"] = seq + 1

        # Send transcript FIRST so user sees what was heard immediately
        await manager.send_json(session_id, {
            "type": "transcription",
            "text": text,
            "is_partial": False,
            "confidence": 0.8,
            "language": detected_lang,
            "sequence": seq,
        })

        # Then translate and send separately
        target_lang = state.get("target_language")
        if target_lang and model_manager.translation_pipeline:
            src_lang = detected_lang or state.get("source_language") or "en"
            if src_lang[:2] != target_lang[:2]:
                try:
                    translated_text = await _translate_long(
                        text, src_lang, target_lang,
                        model_manager.translation_pipeline, loop
                    )
                    await manager.send_json(session_id, {
                        "type": "translation",
                        "translated_text": translated_text,
                        "original_text": text,
                        "source_language": src_lang,
                        "target_language": target_lang,
                        "sequence": seq,
                    })
                except Exception as te:
                    logger.warning(f"Translation failed: {te}")

        # Backend TTS removed - using browser TTS only

    except Exception as e:
        logger.error(f"Commit utterance error: {e}", exc_info=True)
        await manager.send_json(session_id, {"type": "no_speech", "reason": "error"})


def _run_whisper_sync(model, audio: np.ndarray, language):
    """ULTRA-FAST final transcription - greedy mode."""
    segments, info = model.transcribe(
        audio,
        language=language,          # None = auto-detect by Whisper
        beam_size=1,
        word_timestamps=False,
        vad_filter=False,
        temperature=0.0,
        condition_on_previous_text=False,
        without_timestamps=True,
        best_of=1,
        log_prob_threshold=-1.0,
        no_speech_threshold=0.6,
    )
    text = "".join(seg.text for seg in segments)

    # ── Language correction ──────────────────────────────────────────────────
    # Whisper often misdetects short English phrases as Indian/similar-script
    # languages (Malayalam, Tamil, Kannada) because they share Latin vowel
    # patterns. If Whisper is not confident AND the text is pure ASCII/Latin,
    # override the detected language to English.
    detected = info.language
    lang_prob = float(info.language_probability)
    if text and lang_prob < 0.85:
        is_latin = all(ord(c) < 640 for c in text.replace(' ', '').replace("'", ''))
        if is_latin:
            detected = 'en'
    return text, detected


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences for chunked translation of long utterances."""
    import re
    # Split on sentence-ending punctuation followed by space/end
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


async def _translate_long(text: str, src_lang: str, tgt_lang: str, pipeline, loop) -> str:
    """Translate via NLLB greedy inference in thread pool, with sentence chunking >400 chars."""
    nllb = pipeline.nllb
    if not nllb or not nllb.is_loaded:
        raise RuntimeError("NLLB not available")

    src_code = nllb.get_nllb_code(src_lang)
    tgt_code = nllb.get_nllb_code(tgt_lang)
    if not src_code or not tgt_code:
        raise ValueError(f"Unsupported language pair: {src_lang} -> {tgt_lang}")

    import hashlib
    from translation.pipeline import _translation_cache, _store_cache
    from models.schemas import TranslationResponse

    def _translate_chunk(chunk: str) -> str:
        key = hashlib.md5(f"{src_lang}|{tgt_lang}|{chunk}".encode()).hexdigest()
        if key in _translation_cache:
            return _translation_cache[key].translated_text
        result = nllb._infer(chunk, src_code, tgt_code)
        import re as _re
        result = _re.sub(r'\s+([,.!?;:])', r'\1', result)
        result = _re.sub(r'\s{2,}', ' ', result).strip()
        _store_cache(key, TranslationResponse(
            translated_text=result, source_language=src_lang,
            target_language=tgt_lang, model_used="nllb",
            confidence=0.9, processing_time_ms=0
        ))
        return result

    if len(text) <= 400:
        return await loop.run_in_executor(_executor, _translate_chunk, text)

    sentences = _split_sentences(text)
    chunks, current = [], ""
    for s in sentences:
        if current and len(current) + len(s) + 1 > 300:
            chunks.append(current)
            current = s
        else:
            current = (current + " " + s).strip() if current else s
    if current:
        chunks.append(current)

    results = []
    for chunk in chunks:
        r = await loop.run_in_executor(_executor, _translate_chunk, chunk)
        results.append(r)
    return " ".join(results)


# Common Whisper hallucinations on silence/noise
_HALLUCINATION_PHRASES = {
    "thank you", "thanks for watching", "thanks for watching!",
    "thank you for watching", "thank you.", "thanks.", "bye",
    "bye bye", "goodbye", "please subscribe", "like and subscribe",
    "you", ".", "..", "...", "the", "a", "i", "um", "uh",
    "subtitles by", "transcribed by", "captions by",
    "[music]", "[applause]", "[laughter]", "(music)", "(applause)",
}

def _is_hallucination(text: str) -> bool:
    """Detect common Whisper hallucinations on silence or noise."""
    t = text.strip().lower().rstrip(".")
    if len(t) <= 2:
        return True
    if t in _HALLUCINATION_PHRASES:
        return True
    # Whisper sometimes repeats the same word/phrase in a loop
    words = t.split()
    if len(words) >= 4 and len(set(words)) <= 2:
        return True
    return False

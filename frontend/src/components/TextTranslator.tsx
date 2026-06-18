import React, { useState, useRef, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Languages, ArrowRightLeft, Copy, Check, Volume2, Square,
  Loader2, Download, Trash2, FileText, Clock, X,
} from 'lucide-react';
import { SUPPORTED_LANGUAGES } from '@/config/constants';
import { apiService } from '@/services/api';
import { browserTTS } from '@/services/tts';

// ── types ──────────────────────────────────────────────────────────────────────
interface HistoryItem {
  id: string;
  sourceText: string;
  translatedText: string;
  sourceLang: string;
  targetLang: string;
  timestamp: number;
}

// ── tiny helpers ───────────────────────────────────────────────────────────────
function useCopy(text: string) {
  const [copied, setCopied] = useState(false);
  const copy = useCallback(() => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [text]);
  return { copy, copied };
}

function downloadText(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

function downloadAudio(base64: string, filename: string) {
  const bytes = atob(base64);
  const ab = new ArrayBuffer(bytes.length);
  const view = new Uint8Array(ab);
  for (let i = 0; i < bytes.length; i++) view[i] = bytes.charCodeAt(i);
  const blob = new Blob([ab], { type: 'audio/wav' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

const nonAutoLangs = SUPPORTED_LANGUAGES.filter(l => l.code !== 'auto');

// ── main component ─────────────────────────────────────────────────────────────
export default function TextTranslator() {
  const [sourceText, setSourceText] = useState('');
  const [translatedText, setTranslatedText] = useState('');
  const [sourceLang, setSourceLang] = useState('auto');
  const [targetLang, setTargetLang] = useState('es');
  const [isTranslating, setIsTranslating] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoTranslate, setAutoTranslate] = useState(false);
  const [detectedLang, setDetectedLang] = useState<string | null>(null);
  const [meta, setMeta] = useState<{ time: number; model: string; chunks: number } | null>(null);
  const [audioBase64, setAudioBase64] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  const { copy: copyTranslation, copied: copiedTranslation } = useCopy(translatedText);
  const autoTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── translate ────────────────────────────────────────────────────────────────
  const translate = useCallback(async (text: string, src: string, tgt: string) => {
    if (!text.trim() || src === tgt) return;
    setIsTranslating(true);
    setError(null);
    setAudioBase64(null);
    try {
      const res = await apiService.translateLargeText(text, src, tgt);
      setTranslatedText(res.translated_text);
      setDetectedLang(res.detected_language);
      setMeta({ time: res.processing_time_ms, model: res.model_used, chunks: res.chunk_count });
      setHistory(prev => [{
        id: Date.now().toString(),
        sourceText: text.slice(0, 120),
        translatedText: res.translated_text.slice(0, 120),
        sourceLang: res.source_language,
        targetLang: tgt,
        timestamp: Date.now(),
      }, ...prev].slice(0, 20));
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Translation failed.');
    } finally {
      setIsTranslating(false);
    }
  }, []);

  // ── auto-translate debounce ──────────────────────────────────────────────────
  useEffect(() => {
    if (!autoTranslate || !sourceText.trim()) return;
    if (autoTimer.current) clearTimeout(autoTimer.current);
    autoTimer.current = setTimeout(() => translate(sourceText, sourceLang, targetLang), 700);
    return () => { if (autoTimer.current) clearTimeout(autoTimer.current); };
  }, [sourceText, sourceLang, targetLang, autoTranslate, translate]);

  // ── TTS via API (backend), fall back to browser TTS ─────────────────────────
  const speakTranslation = useCallback(async () => {
    if (!translatedText) return;
    if (isSpeaking) { browserTTS.stop(); setIsSpeaking(false); return; }

    // Try backend TTS first for quality
    setIsSynthesizing(true);
    try {
      const res = await apiService.synthesizeSpeech(translatedText.slice(0, 10000), targetLang);
      setAudioBase64(res.audio_base64);
      const audio = new Audio(`data:audio/wav;base64,${res.audio_base64}`);
      setIsSpeaking(true);
      audio.onended = () => setIsSpeaking(false);
      audio.onerror = () => setIsSpeaking(false);
      audio.play();
    } catch {
      // fallback to browser TTS
      setIsSpeaking(true);
      browserTTS.speak(translatedText, targetLang, () => setIsSpeaking(false));
    } finally {
      setIsSynthesizing(false);
    }
  }, [translatedText, targetLang, isSpeaking]);

  const stopSpeech = useCallback(() => {
    browserTTS.stop();
    setIsSpeaking(false);
  }, []);

  const handleSwap = () => {
    if (sourceLang === 'auto') return;
    setSourceLang(targetLang);
    setTargetLang(sourceLang);
    setSourceText(translatedText);
    setTranslatedText(sourceText);
    setDetectedLang(null);
    setMeta(null);
    setAudioBase64(null);
  };

  const handleClear = () => {
    setSourceText('');
    setTranslatedText('');
    setError(null);
    setDetectedLang(null);
    setMeta(null);
    setAudioBase64(null);
    stopSpeech();
  };

  const loadFromHistory = (item: HistoryItem) => {
    setSourceText(item.sourceText);
    setTranslatedText(item.translatedText);
    setSourceLang(item.sourceLang === 'auto' ? 'auto' : item.sourceLang);
    setTargetLang(item.targetLang);
    setShowHistory(false);
  };

  const detectedDisplay = detectedLang
    ? SUPPORTED_LANGUAGES.find(l => l.code === detectedLang)
    : null;

  const charCount = sourceText.length;
  const atLimit = charCount >= 50000;

  return (
    <div className="flex flex-col gap-4 w-full max-w-5xl mx-auto px-4 py-6">

      {/* ── toolbar row ── */}
      <div className="flex flex-wrap items-center gap-2 justify-between">
        {/* Auto-translate toggle */}
        <div
          onClick={() => setAutoTranslate(v => !v)}
          className="flex items-center gap-2 cursor-pointer select-none text-sm text-white/50 hover:text-white/80 transition-colors"
          role="switch"
          aria-checked={autoTranslate}
          aria-label="Auto Translate"
          tabIndex={0}
          onKeyDown={e => e.key === 'Enter' || e.key === ' ' ? setAutoTranslate(v => !v) : undefined}
        >
          <div className={`relative w-9 h-5 rounded-full transition-colors flex-shrink-0 ${autoTranslate ? 'bg-indigo-500' : 'bg-white/10'}`}>
            <div className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${autoTranslate ? 'translate-x-4' : ''}`} />
          </div>
          Auto Translate
        </div>

        <div className="flex items-center gap-2">
          {/* History button */}
          <button
            onClick={() => setShowHistory(h => !h)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
              showHistory ? 'border-indigo-500/40 bg-indigo-500/15 text-indigo-300' : 'border-white/10 bg-white/5 text-white/40 hover:text-white/70'
            }`}
            aria-label="Translation history"
          >
            <Clock size={12} />
            History {history.length > 0 && `(${history.length})`}
          </button>
        </div>
      </div>

      {/* ── history panel ── */}
      <AnimatePresence>
        {showHistory && history.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="rounded-xl border border-white/8 bg-white/[0.03] p-3 flex flex-col gap-2 max-h-52 overflow-y-auto">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-white/40 uppercase tracking-wider">Recent Translations</span>
                <button onClick={() => setHistory([])} className="p-1 text-white/20 hover:text-red-400 transition-colors" aria-label="Clear history">
                  <Trash2 size={12} />
                </button>
              </div>
              {history.map(item => {
                const tgtFlag = SUPPORTED_LANGUAGES.find(l => l.code === item.targetLang)?.flag_emoji ?? '';
                return (
                  <button
                    key={item.id}
                    onClick={() => loadFromHistory(item)}
                    className="flex items-start gap-2 text-left px-2.5 py-2 rounded-lg hover:bg-white/5 transition-colors group"
                  >
                    <span className="text-sm mt-0.5 flex-shrink-0">{tgtFlag}</span>
                    <div className="min-w-0">
                      <p className="text-xs text-white/30 truncate">{item.sourceText}</p>
                      <p className="text-sm text-white/70 truncate group-hover:text-white/90 transition-colors">{item.translatedText}</p>
                    </div>
                    <span className="text-[10px] text-white/15 flex-shrink-0 mt-1">{new Date(item.timestamp).toLocaleTimeString()}</span>
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── language row ── */}
      <div className="flex items-center gap-3">
        <div className="flex-1 flex flex-col gap-1">
          <select
            value={sourceLang}
            onChange={e => setSourceLang(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-3.5 py-2.5 text-sm font-medium text-white appearance-none focus:outline-none focus:border-indigo-500/60 transition-all cursor-pointer"
            aria-label="Source language"
          >
            {SUPPORTED_LANGUAGES.map(l => (
              <option key={l.code} value={l.code} className="bg-[#111]">{l.flag_emoji} {l.name}</option>
            ))}
          </select>
          {detectedDisplay && sourceLang === 'auto' && (
            <p className="text-[10px] text-indigo-400/60 px-1">
              Detected: {detectedDisplay.flag_emoji} {detectedDisplay.name}
            </p>
          )}
        </div>

        <button
          onClick={handleSwap}
          disabled={sourceLang === 'auto'}
          title="Swap languages"
          className="flex-shrink-0 w-9 h-9 flex items-center justify-center rounded-full bg-white/5 border border-white/10 text-white/40 hover:text-white hover:bg-white/10 disabled:opacity-20 disabled:cursor-not-allowed transition-all"
          aria-label="Swap languages"
        >
          <ArrowRightLeft size={15} />
        </button>

        <select
          value={targetLang}
          onChange={e => setTargetLang(e.target.value)}
          className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3.5 py-2.5 text-sm font-medium text-white appearance-none focus:outline-none focus:border-indigo-500/60 transition-all cursor-pointer"
          aria-label="Target language"
        >
          {nonAutoLangs.map(l => (
            <option key={l.code} value={l.code} className="bg-[#111]">{l.flag_emoji} {l.name}</option>
          ))}
        </select>
      </div>

      {/* ── error banner ── */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="flex items-center justify-between gap-2 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm"
            role="alert"
          >
            <span>{error}</span>
            <button onClick={() => setError(null)} aria-label="Dismiss error"><X size={14} /></button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── text panels ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Source */}
        <div className="flex flex-col gap-2">
          <div className="relative rounded-2xl bg-white/[0.04] border border-white/[0.08] focus-within:border-indigo-500/40 transition-colors">
            <textarea
              value={sourceText}
              onChange={e => setSourceText(e.target.value)}
              placeholder="Type or paste text to translate…"
              aria-label="Source text"
              maxLength={50000}
              className="w-full bg-transparent px-4 pt-4 pb-10 text-sm text-white placeholder-white/20 resize-none focus:outline-none min-h-[280px] leading-relaxed pointer-events-auto"
            />
            <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-3 py-2 bg-gradient-to-t from-[#0a0a0f]/80">
              <span className={`text-[10px] font-mono ${atLimit ? 'text-red-400' : 'text-white/20'}`}>
                {charCount.toLocaleString()} / 50,000
              </span>
              {sourceText && (
                <button
                  onClick={handleClear}
                  className="p-1 text-white/20 hover:text-white/60 transition-colors"
                  aria-label="Clear text"
                >
                  <Trash2 size={12} />
                </button>
              )}
            </div>
          </div>

          {/* Translate button */}
          {!autoTranslate && (
            <button
              onClick={() => translate(sourceText, sourceLang, targetLang)}
              disabled={!sourceText.trim() || isTranslating}
              className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold transition-all"
              aria-label="Translate text"
            >
              {isTranslating
                ? <><Loader2 size={15} className="animate-spin" /> Translating…</>
                : <><Languages size={15} /> Translate</>
              }
            </button>
          )}
          {autoTranslate && isTranslating && (
            <div className="flex items-center justify-center gap-2 py-2 text-indigo-400/70 text-xs">
              <Loader2 size={12} className="animate-spin" /> Auto-translating…
            </div>
          )}
        </div>

        {/* Target */}
        <div className="flex flex-col gap-2">
          <div className="relative rounded-2xl bg-indigo-500/[0.06] border border-indigo-500/[0.15] overflow-hidden min-h-[280px]">
            {/* header */}
            <div className="flex items-center justify-between px-4 pt-3 pb-1">
              <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-indigo-400/60">
                {SUPPORTED_LANGUAGES.find(l => l.code === targetLang)?.flag_emoji}{' '}
                {SUPPORTED_LANGUAGES.find(l => l.code === targetLang)?.name}
              </span>
              <div className="flex items-center gap-0.5">
                <button
                  onClick={copyTranslation}
                  disabled={!translatedText}
                  title="Copy translation"
                  className="p-1.5 rounded-lg text-white/25 hover:text-white/70 hover:bg-white/8 transition-all disabled:opacity-0"
                  aria-label="Copy translation"
                >
                  {copiedTranslation ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                </button>
                <button
                  onClick={speakTranslation}
                  disabled={!translatedText || isSynthesizing}
                  title={isSpeaking ? 'Stop speech' : 'Speak translation'}
                  className={`p-1.5 rounded-lg transition-all disabled:opacity-30 ${
                    isSpeaking
                      ? 'text-indigo-400 bg-indigo-500/15 hover:bg-indigo-500/25'
                      : 'text-white/25 hover:text-indigo-400 hover:bg-indigo-500/10'
                  }`}
                  aria-label={isSpeaking ? 'Stop speech' : 'Speak translation'}
                >
                  {isSynthesizing ? (
                    <Loader2 size={13} className="animate-spin" />
                  ) : isSpeaking ? (
                    <Square size={13} fill="currentColor" />
                  ) : (
                    <Volume2 size={13} className={isSpeaking ? 'animate-pulse' : ''} />
                  )}
                </button>
                <button
                  onClick={() => downloadText(translatedText, `translation_${targetLang}.txt`)}
                  disabled={!translatedText}
                  title="Download translation as TXT"
                  className="p-1.5 rounded-lg text-white/25 hover:text-white/70 hover:bg-white/8 transition-all disabled:opacity-0"
                  aria-label="Download translation"
                >
                  <FileText size={13} />
                </button>
                {audioBase64 && (
                  <button
                    onClick={() => downloadAudio(audioBase64, `translation_${targetLang}.wav`)}
                    title="Download audio"
                    className="p-1.5 rounded-lg text-white/25 hover:text-indigo-400 hover:bg-indigo-500/10 transition-all"
                    aria-label="Download audio"
                  >
                    <Download size={13} />
                  </button>
                )}
              </div>
            </div>

            <div className="px-4 pb-10 min-h-[220px]">
              <AnimatePresence mode="wait">
                {isTranslating && !translatedText ? (
                  <motion.div key="loading"
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    className="flex items-center gap-2 text-indigo-400/50 pt-4"
                  >
                    <Loader2 size={15} className="animate-spin" />
                    <span className="text-sm italic">Translating…</span>
                  </motion.div>
                ) : (
                  <motion.p
                    key={translatedText}
                    initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
                    className={`text-sm leading-relaxed whitespace-pre-wrap pt-1 ${
                      translatedText ? 'text-indigo-100' : 'text-indigo-400/20 italic'
                    }`}
                  >
                    {translatedText || 'Translation appears here'}
                  </motion.p>
                )}
              </AnimatePresence>
            </div>

            {/* meta footer */}
            {meta && (
              <div className="absolute bottom-0 left-0 right-0 flex items-center gap-3 px-4 py-2 bg-gradient-to-t from-[#0a0a0f]/80">
                <span className="text-[10px] text-indigo-400/30 font-mono">
                  {meta.time.toFixed(0)}ms · {meta.model}
                  {meta.chunks > 1 ? ` · ${meta.chunks} chunks` : ''}
                </span>
              </div>
            )}
          </div>

          {/* Stop speech button */}
          {isSpeaking && (
            <button
              onClick={stopSpeech}
              className="flex items-center justify-center gap-2 w-full py-2 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm hover:bg-rose-500/15 transition-all"
              aria-label="Stop speech"
            >
              <Square size={13} fill="currentColor" /> Stop Speech
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

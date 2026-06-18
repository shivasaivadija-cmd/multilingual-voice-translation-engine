import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mic, Square, Volume2, Languages, Wifi, WifiOff,
  Loader2, Copy, Check, ChevronRight, Trash2, Clock, Type
} from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { useMicrophone } from '@/hooks/useMicrophone';
import { wsService } from '@/services/websocket';
import { browserTTS } from '@/services/tts';
import { getRomanization } from '@/services/romanization';
import { SUPPORTED_LANGUAGES } from '@/config/constants';
import type { HistoryEntry } from '@/types';
import TextTranslator from '@/components/TextTranslator';

// ── small helpers ──────────────────────────────────────────────────────────────
function useCopy(text: string) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return { copy, copied };
}

function CopyBtn({ text }: { text: string }) {
  const { copy, copied } = useCopy(text);
  return (
    <button onClick={copy} disabled={!text}
      className="p-1.5 rounded-lg text-white/25 hover:text-white/70 hover:bg-white/8 transition-all disabled:opacity-0">
      {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
    </button>
  );
}

function SpeakBtn({ text, lang, size = 13 }: { text: string; lang: string; size?: number }) {
  const [speaking, setSpeaking] = useState(false);
  const speak = () => {
    if (!text) return;
    if (speaking) { browserTTS.stop(); setSpeaking(false); return; }
    setSpeaking(true);
    browserTTS.speak(text, lang, () => setSpeaking(false));
  };
  return (
    <button onClick={speak} disabled={!text}
      title={speaking ? 'Stop' : 'Speak aloud'}
      className={`p-1.5 rounded-lg transition-all disabled:opacity-0 ${
        speaking
          ? 'text-indigo-400 bg-indigo-500/15 hover:bg-indigo-500/25'
          : 'text-white/25 hover:text-indigo-400 hover:bg-indigo-500/10'
      }`}>
      <Volume2 size={size} className={speaking ? 'animate-pulse' : ''} />
    </button>
  );
}

// ── waveform bars ──────────────────────────────────────────────────────────────
function Waveform({ level, isListening, isSpeaking }: { level: number; isListening: boolean; isSpeaking: boolean }) {
  const N = 40;
  const bars = Array.from({ length: N }, (_, i) => {
    const envelope = Math.sin((i / (N - 1)) * Math.PI);
    if (isListening && isSpeaking) return Math.max(6, 6 + level * 80 * envelope);
    if (isListening) return 4 + Math.sin(Date.now() / 600 + i * 0.6) * 1.5;
    return 3;
  });

  return (
    <div className="flex items-center justify-center gap-[2.5px] h-14 w-full">
      {bars.map((h, i) => (
        <motion.div key={i} animate={{ height: `${h}px` }}
          transition={{ type: 'tween', duration: 0.05 }}
          style={{
            width: '2.5px', borderRadius: '999px',
            background: isListening && isSpeaking
              ? `rgba(99,102,241,${0.35 + level * 0.65})`
              : isListening ? 'rgba(99,102,241,0.22)' : 'rgba(255,255,255,0.07)',
          }} />
      ))}
    </div>
  );
}

// ── history item ───────────────────────────────────────────────────────────────
function HistoryItem({ entry, targetLang }: { entry: HistoryEntry; targetLang: string }) {
  const [open, setOpen] = useState(false);
  const flag = SUPPORTED_LANGUAGES.find(l => l.code === entry.target_language)?.flag_emoji ?? '';
  return (
    <div className="rounded-xl bg-white/4 border border-white/6 overflow-hidden">
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-start gap-2 px-3 py-2.5 text-left hover:bg-white/4 transition-all">
        <span className="text-base mt-0.5">{flag}</span>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-white/40 truncate">{entry.original_text}</p>
          <p className="text-sm text-white/80 truncate font-medium">{entry.translated_text}</p>
        </div>
        <ChevronRight size={13} className={`text-white/20 mt-1 flex-shrink-0 transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>
      {open && (
        <div className="px-3 pb-3 border-t border-white/5 pt-2 flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <p className="text-xs text-white/30 flex-1">{new Date(entry.created_at).toLocaleTimeString()}</p>
            <CopyBtn text={entry.original_text} />
            <CopyBtn text={entry.translated_text} />
            <SpeakBtn text={entry.translated_text} lang={entry.target_language} />
          </div>
          {(() => {
            const roman = getRomanization(entry.translated_text, entry.target_language);
            return roman ? (
              <p className="text-[10px] text-white/25 italic tracking-wide">{roman}</p>
            ) : null;
          })()}
        </div>
      )}
    </div>
  );
}

// ── main app ───────────────────────────────────────────────────────────────────
export default function App() {
  const {
    isListening, setListening,
    currentTranscript, currentTranslation,
    sourceLanguage, targetLanguage,
    setSourceLanguage, setTargetLanguage,
    connectionStatus, error, setError,
    history, isSpeaking, noSpeechHint, isProcessing, detectedLanguage,
  } = useAppStore();

  const { startRecording, stopRecording, audioLevel } = useMicrophone();
  const [showHistory, setShowHistory] = useState(false);
  const [activeTab, setActiveTab] = useState<'voice' | 'text'>('voice');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { wsService.connect(); return () => { wsService.disconnect(); browserTTS.stop(); }; }, []);

  // Auto-speak new translations INSTANTLY for speed
  const prevTranslation = useRef('');
  useEffect(() => {
    if (currentTranslation && currentTranslation !== prevTranslation.current) {
      prevTranslation.current = currentTranslation;
      // 0.3s delay - minimal but still readable
      setTimeout(() => {
        if (useAppStore.getState().currentTranslation === currentTranslation) {
          browserTTS.speak(currentTranslation, targetLanguage);
        }
      }, 300);
    }
  }, [currentTranslation, targetLanguage]);

  const targetLanguages = SUPPORTED_LANGUAGES.filter(l => l.code !== 'auto');
  const getLang = (code: string) => SUPPORTED_LANGUAGES.find(l => l.code === code);

  const toggleListening = async () => {
    if (isListening) {
      setListening(false);
      stopRecording();
    } else {
      setError(null);
      setListening(true);
      await startRecording();
    }
  };

  const handleSwap = () => {
    if (sourceLanguage === 'auto') return;
    setSourceLanguage(targetLanguage);
    setTargetLanguage(sourceLanguage);
  };

  const connected = connectionStatus === 'connected';
  const connecting = connectionStatus === 'connecting';
  const srcLang = getLang(sourceLanguage);
  const tgtLang = getLang(targetLanguage);

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white font-sans flex flex-col">

      {/* ── Header ── */}
      <header className="flex items-center justify-between px-5 py-3.5 border-b border-white/6 backdrop-blur-sm sticky top-0 z-20 bg-[#0a0a0f]/90">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Languages size={15} />
          </div>
          <span className="font-semibold text-sm tracking-tight text-white/90">Voice Translator Pro</span>
        </div>
        <div className="flex items-center gap-3">
          {/* Tab switcher */}
          <div className="flex items-center bg-white/5 border border-white/8 rounded-xl p-0.5">
            <button
              onClick={() => setActiveTab('voice')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'voice'
                  ? 'bg-indigo-500/25 text-indigo-300 shadow'
                  : 'text-white/35 hover:text-white/60'
              }`}
              aria-label="Voice translation mode"
            >
              <Mic size={11} /> Voice
            </button>
            <button
              onClick={() => setActiveTab('text')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'text'
                  ? 'bg-indigo-500/25 text-indigo-300 shadow'
                  : 'text-white/35 hover:text-white/60'
              }`}
              aria-label="Text translation mode"
            >
              <Type size={11} /> Text
            </button>
          </div>
          {/* Connection pill */}
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
            connected ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' :
            connecting ? 'border-amber-500/30 bg-amber-500/10 text-amber-400' :
            'border-red-500/30 bg-red-500/10 text-red-400'
          }`}>
            {connecting ? <Loader2 size={10} className="animate-spin" /> :
             connected ? <Wifi size={10} /> : <WifiOff size={10} />}
            {connecting ? 'Connecting' : connected ? 'Live' : 'Offline'}
          </div>
          {/* History toggle */}
          <button onClick={() => setShowHistory(h => !h)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all ${
              showHistory
                ? 'border-indigo-500/40 bg-indigo-500/15 text-indigo-300'
                : 'border-white/10 bg-white/5 text-white/40 hover:text-white/70'
            }`}>
            <Clock size={10} />
            History {history.length > 0 && `(${history.length})`}
          </button>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">

        {/* ── Text Translation tab ── */}
        {activeTab === 'text' && (
          <div className="flex-1 overflow-y-auto min-h-0">
            <TextTranslator />
          </div>
        )}

        {/* ── Voice Translation tab ── */}
        {activeTab === 'voice' && (<>
        {/* ── Main panel ── */}
        <main className="flex-1 flex flex-col items-center px-4 py-6 max-w-2xl mx-auto w-full gap-5 overflow-y-auto min-h-0">

          {/* Language selector */}
          <div className="w-full flex items-center gap-2">
            <select value={sourceLanguage} onChange={e => setSourceLanguage(e.target.value)}
              className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3.5 py-2.5 text-sm font-medium text-white appearance-none focus:outline-none focus:border-indigo-500/60 focus:bg-white/7 transition-all cursor-pointer truncate">
              {SUPPORTED_LANGUAGES.map(l => (
                <option key={l.code} value={l.code} className="bg-[#111]">{l.flag_emoji} {l.name}</option>
              ))}
            </select>

            <button onClick={handleSwap} disabled={sourceLanguage === 'auto'}
              className="flex-shrink-0 w-9 h-9 flex items-center justify-center rounded-full bg-white/5 border border-white/10 text-white/40 hover:text-white hover:bg-white/10 disabled:opacity-20 disabled:cursor-not-allowed transition-all text-base">
              ⇄
            </button>

            <select value={targetLanguage} onChange={e => setTargetLanguage(e.target.value)}
              className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3.5 py-2.5 text-sm font-medium text-white appearance-none focus:outline-none focus:border-indigo-500/60 focus:bg-white/7 transition-all cursor-pointer truncate">
              {targetLanguages.map(l => (
                <option key={l.code} value={l.code} className="bg-[#111]">{l.flag_emoji} {l.name}</option>
              ))}
            </select>
          </div>

          {/* Error banner */}
          <AnimatePresence>
            {error && (
              <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="w-full flex items-center justify-between gap-2 px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                <span>{error}</span>
                <button onClick={() => setError(null)} className="text-red-400/60 hover:text-red-400">✕</button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Transcript cards */}
          <div className="w-full flex flex-col gap-3 flex-1">

            {/* Source card */}
            <div className="rounded-2xl bg-white/[0.04] border border-white/[0.08] p-4 flex flex-col min-h-[130px] max-h-64 overflow-y-auto">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-white/30">
                  {srcLang?.flag_emoji} {srcLang?.name ?? sourceLanguage}
                </span>
                <div className="flex items-center gap-1">
                  {isListening && (
                    <span className={`flex items-center gap-1 text-[10px] font-medium ${isSpeaking ? 'text-indigo-400' : 'text-white/25'}`}>
                      {isSpeaking
                        ? <><span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse inline-block" /> Speaking</>
                        : <><span className="w-1.5 h-1.5 rounded-full bg-white/20 inline-block" /> Waiting</>
                      }
                    </span>
                  )}
                  <CopyBtn text={currentTranscript} />
                </div>
              </div>
              <motion.p 
                key={currentTranscript}
                initial={{ opacity: 0.7 }} 
                animate={{ opacity: 1 }}
                transition={{ duration: 0.15 }}
                className={`flex-1 text-lg leading-relaxed ${currentTranscript ? 'text-white font-light' : 'text-white/20 italic text-base'}`}>
                {currentTranscript || (isListening ? 'Speak now…' : 'Tap the mic to start')}
              </motion.p>
              <AnimatePresence>
                {noSpeechHint && !currentTranscript && (
                  <motion.p
                    initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                    className="text-xs text-amber-400/70 mt-1.5 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400/70 flex-shrink-0 inline-block" />
                    {noSpeechHint}
                  </motion.p>
                )}
              </AnimatePresence>
            </div>

            {/* Arrow */}
            <div className="flex items-center justify-center">
              <div className="flex items-center gap-2 text-white/15 text-xs">
                <div className="h-px w-12 bg-white/10" />
                <span>↓ {tgtLang?.flag_emoji}</span>
                <div className="h-px w-12 bg-white/10" />
              </div>
            </div>

            {/* Translation card */}
            <div className="rounded-2xl bg-indigo-500/[0.06] border border-indigo-500/[0.15] p-4 flex flex-col min-h-[130px] max-h-72 overflow-y-auto">

              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-indigo-400/60">
                  {tgtLang?.flag_emoji} {tgtLang?.name ?? targetLanguage}
                </span>
                <div className="flex items-center gap-0.5">
                  <CopyBtn text={currentTranslation} />
                  <SpeakBtn text={currentTranslation} lang={targetLanguage} />
                </div>
              </div>
              <AnimatePresence mode="wait">
                <motion.div key={currentTranslation + String(isProcessing)}
                  initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
                  {isProcessing && !currentTranslation ? (
                    <div className="flex items-center gap-2 text-indigo-400/50">
                      <Loader2 size={14} className="animate-spin" />
                      <span className="text-sm italic">Transcribing…</span>
                    </div>
                  ) : (
                    <p className={`text-lg leading-relaxed font-medium ${
                      currentTranslation ? 'text-indigo-100' : 'text-indigo-400/20 italic text-base'
                    }`}>
                      {currentTranslation || 'Translation appears here'}
                    </p>
                  )}
                  {/* Romanization / pronunciation hint */}
                  {currentTranslation && (() => {
                    const roman = getRomanization(currentTranslation, targetLanguage);
                    return roman ? (
                      <p className="mt-1.5 text-xs text-indigo-300/40 font-normal tracking-wide italic">
                        {roman}
                      </p>
                    ) : null;
                  })()}
                </motion.div>
              </AnimatePresence>
            </div>
          </div>

          {/* Waveform */}
          <Waveform level={audioLevel} isListening={isListening} isSpeaking={isSpeaking} />

          {/* Mic button */}
          <div className="flex flex-col items-center gap-2.5 pb-2">
            <div className="relative">
              {isListening && (
                <motion.div className="absolute inset-0 rounded-full pointer-events-none"
                  animate={{ scale: [1, isSpeaking ? 1.7 : 1.4, 1], opacity: [0.25, 0, 0.25] }}
                  transition={{ duration: isSpeaking ? 0.8 : 1.8, repeat: Infinity }}
                  style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.5) 0%, transparent 70%)' }} />
              )}
              <motion.button
                whileHover={{ scale: connected ? 1.05 : 1 }}
                whileTap={{ scale: connected ? 0.94 : 1 }}
                onClick={connected ? toggleListening : undefined}
                disabled={!connected}
                className={`relative z-10 w-[72px] h-[72px] rounded-full flex items-center justify-center shadow-2xl transition-all duration-300 ${
                  !connected ? 'bg-white/8 cursor-not-allowed' :
                  isListening
                    ? 'bg-gradient-to-br from-rose-500 to-red-600 shadow-red-500/25'
                    : 'bg-gradient-to-br from-indigo-500 to-violet-600 shadow-indigo-500/30 hover:shadow-indigo-500/50'
                }`}>
                {isListening
                  ? <Square size={26} fill="white" className="text-white" />
                  : <Mic size={26} className="text-white" />}
              </motion.button>
            </div>
            <p className="text-xs text-white/25 font-medium">
              {!connected ? 'Connecting…'
                : isListening
                  ? isProcessing ? '⏳ Processing…'
                  : isSpeaking ? '🎙 Detecting speech…' : '⏸ Waiting for voice…'
                  : 'Tap to start translating'}
            </p>
          </div>

          <div ref={bottomRef} />
        </main>

        {/* ── History sidebar ── */}
        <AnimatePresence>
          {showHistory && (
            <motion.aside
              initial={{ width: 0, opacity: 0 }} animate={{ width: 300, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }} transition={{ duration: 0.25 }}
              className="border-l border-white/6 bg-white/[0.02] flex flex-col overflow-hidden flex-shrink-0">
              <div className="flex items-center justify-between px-4 py-3 border-b border-white/6">
                <span className="text-sm font-semibold text-white/70">History</span>
                {history.length > 0 && (
                  <button onClick={() => useAppStore.setState({ history: [] })}
                    className="p-1.5 rounded-lg text-white/25 hover:text-red-400 hover:bg-red-500/10 transition-all">
                    <Trash2 size={13} />
                  </button>
                )}
              </div>
              <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
                {history.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full gap-2 text-center">
                    <Clock size={24} className="text-white/10" />
                    <p className="text-xs text-white/20">Translations will appear here</p>
                  </div>
                ) : (
                  history.map(entry => (
                    <HistoryItem key={entry.id} entry={entry} targetLang={entry.target_language} />
                  ))
                )}
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
        </>)}
      </div>
    </div>
  );
}

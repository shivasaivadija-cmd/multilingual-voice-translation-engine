import { WS_BASE_URL } from '@/config/constants';
import { useAppStore } from '@/store/useAppStore';
import { browserTTS } from '@/services/tts';

let vadClearTimer: ReturnType<typeof setTimeout> | null = null;
let noSpeechTimer: ReturnType<typeof setTimeout> | null = null;

function setNoSpeechHint(hint: string | null) {
  const store = useAppStore.getState();
  store.setNoSpeechHint(hint);
  if (noSpeechTimer) clearTimeout(noSpeechTimer);
  if (hint) noSpeechTimer = setTimeout(() => useAppStore.getState().setNoSpeechHint(null), 3000);
}

class WebSocketService {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private isIntentionalClose = false;
  private audioQueue: string[] = [];
  private isPlayingAudio = false;

  constructor() {
    // Stable session ID per browser tab — persists across HMR reloads
    const stored = sessionStorage.getItem('ws_session_id');
    if (stored) {
      this.sessionId = stored;
    } else {
      this.sessionId = crypto.randomUUID();
      sessionStorage.setItem('ws_session_id', this.sessionId);
    }
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) return;
    this.isIntentionalClose = false;
    useAppStore.getState().setConnectionStatus('connecting');
    try {
      this.ws = new WebSocket(`${WS_BASE_URL}/${this.sessionId}`);
      this.ws.binaryType = 'arraybuffer';
      this.ws.onopen = () => {
        useAppStore.getState().setConnectionStatus('connected');
        this.reconnectAttempts = 0;
        this.startPing();
        this.sendConfig();
      };
      this.ws.onmessage = (e) => this.handleMessage(e.data);
      this.ws.onclose = () => {
        useAppStore.getState().setConnectionStatus('disconnected');
        this.stopPing();
        if (!this.isIntentionalClose) this.attemptReconnect();
      };
      this.ws.onerror = () => {
        useAppStore.getState().setConnectionStatus('disconnected');
      };
    } catch {
      useAppStore.getState().setConnectionStatus('disconnected');
    }
  }

  private startPing() {
    this.pingInterval = setInterval(() => this.sendJson({ type: 'ping' }), 15000);
  }

  private stopPing() {
    if (this.pingInterval) { clearInterval(this.pingInterval); this.pingInterval = null; }
  }

  private attemptReconnect() {
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      useAppStore.getState().setError('Connection lost. Please refresh.');
      return;
    }
    this.reconnectAttempts++;
    this.reconnectTimeout = setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts);
  }

  private handleMessage(data: string | ArrayBuffer) {
    if (data instanceof ArrayBuffer) return;
    try {
      const msg = JSON.parse(data as string);
      const store = useAppStore.getState();
      switch (msg.type) {
        case 'transcription':
          if (msg.is_partial) break;  // ignore partials — only show final clean result
          setNoSpeechHint(null);
          store.setIsProcessing(false);
          store.setDetectedLanguage(msg.language || null);
          if (store.sourceLanguage === 'auto' && msg.language) {
            store.setSourceLanguage(msg.language);
          }
          store.setCurrentTranscript(msg.text, msg.is_partial ?? false);
          break;
        case 'translation':
          store.setCurrentTranslation(msg.translated_text);
          store.addHistoryEntry({
            id: crypto.randomUUID(),
            original_text: msg.original_text || store.currentTranscript,
            translated_text: msg.translated_text,
            source_language: msg.source_language || store.sourceLanguage,
            target_language: msg.target_language || store.targetLanguage,
            confidence: msg.confidence ?? 0.8,
            duration: 0,
            created_at: new Date().toISOString(),
            is_favorite: false,
          });
          break;
        case 'retranslation':
          store.setIsProcessing(false);
          store.setCurrentTranslation(msg.translation);
          browserTTS.speak(msg.translation, store.targetLanguage);
          break;
        case 'vad':
          if (msg.is_speech) {
            store.setIsSpeaking(true);
            if (vadClearTimer) clearTimeout(vadClearTimer);
            vadClearTimer = setTimeout(() => {
              useAppStore.getState().setIsSpeaking(false);
              // After speech stops, show processing state
              useAppStore.getState().setIsProcessing(true);
            }, 700);
          }
          break;
        case 'tts_audio':
          this.queueAudio(msg.audio_base64);
          break;
        case 'no_speech': {
          store.setIsProcessing(false);
          const hints: Record<string, string> = {
            unclear: "Couldn't make that out — try speaking more clearly",
            noise:   'Noise detected, not speech — try again',
            error:   'Recognition failed — try again',
          };
          setNoSpeechHint(hints[msg.reason as string] ?? "Didn't catch that — try again");
          break;
        }
        case 'error':
          store.setError(msg.message);
          break;
        case 'listening_started':
          store.clearTranscript();
          store.setDetectedLanguage(null);
          break;
      }
    } catch { /* ignore */ }
  }

  private queueAudio(base64: string) {
    this.audioQueue.push(base64);
    if (!this.isPlayingAudio) this.playNextAudio();
  }

  private async playNextAudio() {
    if (!this.audioQueue.length) { this.isPlayingAudio = false; return; }
    this.isPlayingAudio = true;
    const base64 = this.audioQueue.shift()!;
    try {
      const audio = new Audio(`data:audio/wav;base64,${base64}`);
      await new Promise<void>((res) => {
        audio.onended = () => res();
        audio.onerror = () => res();
        audio.play().catch(() => res());
      });
    } catch { /* ignore */ }
    this.playNextAudio();
  }

  sendAudioChunk(chunk: ArrayBuffer) {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(chunk);
  }

  sendJson(payload: object) {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(payload));
  }

  sendConfig() {
    const store = useAppStore.getState();
    this.sendJson({
      type: 'config',
      source_language: store.sourceLanguage === 'auto' ? null : store.sourceLanguage,
      target_language: store.targetLanguage,
    });
  }

  retranslate(text: string, sourceLang: string, targetLang: string) {
    useAppStore.getState().setIsProcessing(true);
    useAppStore.getState().setCurrentTranslation('');
    this.sendJson({
      type: 'retranslate',
      text,
      source_language: sourceLang === 'auto' ? null : sourceLang,
      target_language: targetLang,
    });
  }

  startListening() { this.sendJson({ type: 'start_listening' }); }
  stopListening() { this.sendJson({ type: 'stop_listening' }); }

  disconnect() {
    this.isIntentionalClose = true;
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    this.stopPing();
    if (this.ws) {
      if (this.ws.readyState === WebSocket.CONNECTING) this.ws.onopen = () => this.ws?.close();
      else this.ws.close();
      this.ws = null;
    }
  }
}

export const wsService = new WebSocketService();

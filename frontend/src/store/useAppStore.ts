import { create } from 'zustand';
import type { AppState, HistoryEntry } from '@/types';
import { wsService } from '@/services/websocket';

export const useAppStore = create<AppState & { isSpeaking: boolean; setIsSpeaking: (v: boolean) => void }>((set) => ({
  isListening: false,
  sourceLanguage: 'auto',
  targetLanguage: 'es',
  connectionStatus: 'disconnected',
  currentTranscript: '',
  currentTranslation: '',
  isPartial: false,
  error: null,
  history: [],
  settings: {},
  isSpeaking: false,
  noSpeechHint: null,
  isProcessing: false,
  detectedLanguage: null,

  setIsSpeaking: (v) => set({ isSpeaking: v }),
  setNoSpeechHint: (hint) => set({ noSpeechHint: hint }),
  setIsProcessing: (v) => set({ isProcessing: v }),
  setDetectedLanguage: (lang) => set({ detectedLanguage: lang }),

  setListening: (isListening) => {
    set({ isListening });
    if (isListening) wsService.startListening();
    else wsService.stopListening();
  },

  setSourceLanguage: (lang) => {
    set({ sourceLanguage: lang });
    wsService.sendConfig();
    // Re-translate if there's an existing transcript
    const { currentTranscript, targetLanguage } = useAppStore.getState();
    if (currentTranscript && lang !== 'auto') {
      wsService.retranslate(currentTranscript, lang, targetLanguage);
    }
  },

  setTargetLanguage: (lang) => {
    set({ targetLanguage: lang });
    wsService.sendConfig();
    // Re-translate existing transcript into the new language immediately
    const { currentTranscript, sourceLanguage } = useAppStore.getState();
    if (currentTranscript) {
      wsService.retranslate(currentTranscript, sourceLanguage, lang);
    }
  },

  setConnectionStatus: (status) => set({ connectionStatus: status }),

  setCurrentTranscript: (text, isPartial) => set({ currentTranscript: text, isPartial }),

  setCurrentTranslation: (text) => set({ currentTranslation: text }),

  setError: (error) => set({ error }),

  addHistoryEntry: (entry: HistoryEntry) =>
    set((state) => ({ history: [entry, ...state.history].slice(0, 50) })),

  clearTranscript: () => set({ currentTranscript: '', currentTranslation: '', isPartial: false }),
}));

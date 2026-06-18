export interface Language {
  code: string;
  name: string;
  flag_emoji?: string;
}

export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
  prob: number;
}

export interface TranscriptionSegment {
  text: string;
  start: number;
  end: number;
  language: string;
  confidence: number;
  is_partial: boolean;
  words?: WordTimestamp[];
}

export interface TranslationResult {
  translated_text: string;
  source_language: string;
  target_language: string;
  confidence: number;
}

export interface HistoryEntry {
  id: string;
  original_text: string;
  translated_text: string;
  source_language: string;
  target_language: string;
  confidence: number;
  duration: number;
  created_at: string;
  is_favorite: boolean;
}

export interface AppState {
  isListening: boolean;
  sourceLanguage: string;
  targetLanguage: string;
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
  currentTranscript: string;
  currentTranslation: string;
  isPartial: boolean;
  error: string | null;
  history: HistoryEntry[];
  settings: Record<string, any>;
  noSpeechHint: string | null;
  isProcessing: boolean;
  detectedLanguage: string | null;

  setListening: (isListening: boolean) => void;
  setSourceLanguage: (lang: string) => void;
  setTargetLanguage: (lang: string) => void;
  setConnectionStatus: (status: 'connected' | 'disconnected' | 'connecting') => void;
  setCurrentTranscript: (text: string, isPartial: boolean) => void;
  setCurrentTranslation: (text: string) => void;
  setError: (error: string | null) => void;
  addHistoryEntry: (entry: HistoryEntry) => void;
  clearTranscript: () => void;
  setNoSpeechHint: (hint: string | null) => void;
  setIsProcessing: (v: boolean) => void;
  setDetectedLanguage: (lang: string | null) => void;
  isSpeaking?: boolean;
  setIsSpeaking?: (v: boolean) => void;
}

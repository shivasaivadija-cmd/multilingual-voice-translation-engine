import axios from 'axios';
import { API_BASE_URL } from '@/config/constants';
import type { HistoryEntry } from '@/types';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export const apiService = {
  // Health
  checkHealth: async () => {
    const response = await api.get('/health');
    return response.data;
  },

  // History
  getHistory: async (page = 1, pageSize = 20) => {
    const response = await api.get(`/history/?page=${page}&page_size=${pageSize}`);
    return response.data;
  },

  toggleFavorite: async (id: string) => {
    const response = await api.post(`/history/${id}/favorite`);
    return response.data;
  },

  deleteHistoryEntry: async (id: string) => {
    const response = await api.delete(`/history/${id}`);
    return response.data;
  },

  clearHistory: async () => {
    const response = await api.delete('/history/');
    return response.data;
  },

  // Speech API fallback
  transcribeAudio: async (audioBlob: Blob, language?: string) => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'audio.webm');
    if (language && language !== 'auto') {
      formData.append('language', language);
    }
    const response = await api.post('/speech/transcribe', formData);
    return response.data;
  },

  // Translation API fallback
  translateText: async (text: string, sourceLang: string, targetLang: string) => {
    const response = await api.post('/translation/translate', {
      text,
      source_language: sourceLang,
      target_language: targetLang,
    });
    return response.data;
  },

  // Large text translation with chunking
  translateLargeText: async (
    text: string,
    sourceLang: string,
    targetLang: string,
    saveHistory = true,
  ) => {
    const response = await api.post(
      '/translation/translate-text',
      { text, source_language: sourceLang, target_language: targetLang, save_history: saveHistory },
      { timeout: 120000 },
    );
    return response.data as {
      translated_text: string;
      source_language: string;
      target_language: string;
      detected_language: string | null;
      model_used: string;
      confidence: number;
      processing_time_ms: number;
      char_count: number;
      chunk_count: number;
    };
  },

  // TTS API fallback
  synthesizeSpeech: async (text: string, language: string, voice?: string) => {
    const response = await api.post(
      '/tts/synthesize',
      { text, language, voice },
      { timeout: 60000 },
    );
    return response.data as { audio_base64: string; sample_rate: number; duration: number; voice_used: string };
  },
};

// BCP-47 locale map - prefer locales with better native speaker voices
const LANG_TO_BCP47: Record<string, string> = {
  en: 'en-US', es: 'es-ES', fr: 'fr-FR', de: 'de-DE', it: 'it-IT',
  pt: 'pt-BR', ru: 'ru-RU', zh: 'zh-CN', ja: 'ja-JP', ko: 'ko-KR',
  ar: 'ar-SA', hi: 'hi-IN', te: 'te-IN', ta: 'ta-IN', kn: 'kn-IN',
  ml: 'ml-IN', mr: 'mr-IN', bn: 'bn-IN', gu: 'gu-IN', pa: 'pa-IN',
  ur: 'ur-PK', tr: 'tr-TR', nl: 'nl-NL', pl: 'pl-PL', sv: 'sv-SE',
  no: 'nb-NO', da: 'da-DK', fi: 'fi-FI', cs: 'cs-CZ', sk: 'sk-SK',
  ro: 'ro-RO', hu: 'hu-HU', uk: 'uk-UA', bg: 'bg-BG', hr: 'hr-HR',
  sr: 'sr-RS', el: 'el-GR', he: 'he-IL', fa: 'fa-IR', th: 'th-TH',
  vi: 'vi-VN', id: 'id-ID', ms: 'ms-MY', sw: 'sw-KE', af: 'af-ZA',
  ca: 'ca-ES', lt: 'lt-LT', lv: 'lv-LV', et: 'et-EE',
};

// Telugu-specific voice name patterns (Windows has Heera, mobile has native voices)
const TELUGU_VOICE_PATTERNS = ['heera', 'telugu', 'te-in', 'తెలుగు'];

// Keywords that indicate a higher-quality neural/online voice
const QUALITY_KEYWORDS = ['google', 'microsoft', 'neural', 'natural', 'premium', 'enhanced', 'online'];

// Clean up NLLB output artifacts before speaking
function cleanForSpeech(text: string): string {
  return text
    .replace(/\s+([,.!?;:])/g, '$1')   // remove space before punctuation
    .replace(/([.!?])\s*([.!?])+/g, '$1') // collapse duplicate sentence-enders
    .replace(/\s{2,}/g, ' ')            // collapse multiple spaces
    .replace(/^\s+|\s+$/g, '')          // trim
    .replace(/\[.*?\]|\(.*?\)/g, '')    // strip bracketed notes like [music]
    .replace(/\s+([,.!?;:])/g, '$1');   // second pass after bracket removal
}

// Split text into natural spoken sentences for paced delivery
function splitIntoSentences(text: string): string[] {
  // Split on . ! ? but keep the punctuation attached
  const parts = text.match(/[^.!?]+[.!?]+|[^.!?]+$/g) ?? [text];
  return parts.map(s => s.trim()).filter(s => s.length > 1);
}

// Pick the best available voice for a locale
function pickBestVoice(voices: SpeechSynthesisVoice[], locale: string, langCode: string): SpeechSynthesisVoice | null {
  // Score each candidate voice
  const candidates = voices.filter(v =>
    v.lang === locale || v.lang.startsWith(langCode) || v.lang.startsWith(locale.split('-')[0])
  );
  if (!candidates.length) return null;

  const scored = candidates.map(v => {
    let score = 0;
    const name = v.name.toLowerCase();
    const lang = v.lang.toLowerCase();
    
    if (v.lang === locale) score += 10;                          // exact locale match
    if (QUALITY_KEYWORDS.some(k => name.includes(k))) score += 5; // neural/premium voice
    if (!v.localService) score += 3;                             // online voices are better
    
    // Telugu-specific: prioritize native Telugu voices (Microsoft Heera, Google Telugu)
    if (langCode === 'te' && TELUGU_VOICE_PATTERNS.some(p => name.includes(p) || lang.includes(p))) {
      score += 15;  // highest priority for Telugu native voices
    }
    
    return { v, score };
  });

  scored.sort((a, b) => b.score - a.score);
  return scored[0].v;
}

class BrowserTTSService {
  private synth = window.speechSynthesis;
  private queue: SpeechSynthesisUtterance[] = [];
  private speaking = false;

  isSupported(): boolean {
    return 'speechSynthesis' in window;
  }

  speak(text: string, langCode: string, onEnd?: () => void): void {
    if (!this.isSupported() || !text.trim()) return;
    this.stop();

    const cleaned = cleanForSpeech(text);
    const locale = LANG_TO_BCP47[langCode] ?? langCode;
    const sentences = splitIntoSentences(cleaned);

    // Build utterances with a short delay between voices loading
    const buildAndSpeak = () => {
      const voices = this.synth.getVoices();
      const bestVoice = pickBestVoice(voices, locale, langCode);

      this.queue = sentences.map((sentence, i) => {
        const u = new SpeechSynthesisUtterance(sentence);
        u.lang = locale;
        
        // Telugu needs slower rate for clarity (complex script)
        u.rate = langCode === 'te' ? 0.65 : 0.75;
        u.pitch = 1.0;
        u.volume = 1.0;
        if (bestVoice) u.voice = bestVoice;

        if (i === sentences.length - 1) {
          u.onend = () => { this.speaking = false; onEnd?.(); };
          u.onerror = () => { this.speaking = false; onEnd?.(); };
        }
        return u;
      });

      this.speaking = true;
      this._playQueue();
    };

    // Chrome loads voices async on first call — wait up to 200ms
    if (this.synth.getVoices().length > 0) {
      buildAndSpeak();
    } else {
      const handler = () => { buildAndSpeak(); this.synth.removeEventListener('voiceschanged', handler); };
      this.synth.addEventListener('voiceschanged', handler);
      setTimeout(buildAndSpeak, 200);
    }
  }

  private _playQueue(): void {
    if (!this.queue.length) { this.speaking = false; return; }
    const u = this.queue.shift()!;
    this.synth.speak(u);
    // After each sentence, 300ms pause for Telugu, 250ms for others
    const pauseMs = u.lang.startsWith('te-') ? 300 : 250;
    u.onend = (orig => (e: SpeechSynthesisEvent) => {
      orig?.(e);
      if (this.queue.length) setTimeout(() => this._playQueue(), pauseMs);
    })(u.onend as any);
  }

  stop(): void {
    this.queue = [];
    this.speaking = false;
    this.synth.cancel();
  }

  isSpeaking(): boolean {
    return this.speaking;
  }
}

export const browserTTS = new BrowserTTSService();

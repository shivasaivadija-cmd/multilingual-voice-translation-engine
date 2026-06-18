import React from 'react';
import { SUPPORTED_LANGUAGES } from '@/config/constants';
import { ArrowRightLeft } from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';

export const LanguageSelector: React.FC = () => {
  const { sourceLanguage, targetLanguage, setSourceLanguage, setTargetLanguage } = useAppStore();

  const targetLanguages = SUPPORTED_LANGUAGES.filter(l => l.code !== 'auto');

  const handleSwap = () => {
    if (sourceLanguage === 'auto') return;
    setSourceLanguage(targetLanguage);
    setTargetLanguage(sourceLanguage);
  };

  return (
    <div className="flex items-center justify-center gap-4 py-4 w-full max-w-2xl mx-auto">
      <div className="flex-1">
        <select 
          value={sourceLanguage}
          onChange={(e) => setSourceLanguage(e.target.value)}
          className="w-full appearance-none rounded-2xl bg-white p-4 pl-6 text-lg font-medium text-slate-800 shadow-sm ring-1 ring-slate-200 transition-all hover:ring-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:bg-slate-800 dark:text-white dark:ring-slate-700"
        >
          {SUPPORTED_LANGUAGES.map(lang => (
            <option key={lang.code} value={lang.code}>
              {lang.flag_emoji} {lang.name}
            </option>
          ))}
        </select>
      </div>

      <button
        onClick={handleSwap}
        disabled={sourceLanguage === 'auto'}
        className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-500 transition-colors hover:bg-slate-200 hover:text-slate-800 disabled:opacity-40 disabled:cursor-not-allowed dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-200"
        aria-label="Swap languages"
      >
        <ArrowRightLeft size={20} />
      </button>

      <div className="flex-1">
        <select 
          value={targetLanguage}
          onChange={(e) => setTargetLanguage(e.target.value)}
          className="w-full appearance-none rounded-2xl bg-white p-4 pl-6 text-lg font-medium text-slate-800 shadow-sm ring-1 ring-slate-200 transition-all hover:ring-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:bg-slate-800 dark:text-white dark:ring-slate-700"
        >
          {targetLanguages.map(lang => (
            <option key={lang.code} value={lang.code}>
              {lang.flag_emoji} {lang.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

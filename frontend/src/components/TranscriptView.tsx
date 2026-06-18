import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2 } from 'lucide-react';

interface TranscriptViewProps {
  transcript: string;
  translation: string;
  isPartial: boolean;
  sourceLanguage: string;
  targetLanguage: string;
}

export const TranscriptView: React.FC<TranscriptViewProps> = ({
  transcript,
  translation,
  isPartial,
  sourceLanguage,
  targetLanguage
}) => {
  return (
    <div className="flex w-full flex-col gap-6">
      <div className="glass flex min-h-[160px] flex-col rounded-3xl p-6 transition-all">
        <div className="mb-2 flex items-center justify-between text-sm font-medium text-slate-500 dark:text-slate-400">
          <span className="uppercase tracking-wider">{sourceLanguage} (Source)</span>
          {isPartial && <Loader2 size={16} className="animate-spin text-primary-500" />}
        </div>
        <p className="flex-1 text-2xl font-light leading-relaxed text-slate-800 dark:text-slate-100">
          {transcript || (
            <span className="text-slate-300 dark:text-slate-600 italic">
              Listening... Speak to translate
            </span>
          )}
        </p>
      </div>

      <div className="glass flex min-h-[160px] flex-col rounded-3xl border-primary-200 bg-primary-50/50 p-6 dark:border-primary-900/50 dark:bg-primary-900/20">
        <div className="mb-2 flex items-center justify-between text-sm font-medium text-primary-600 dark:text-primary-400">
          <span className="uppercase tracking-wider">{targetLanguage} (Translation)</span>
        </div>
        <AnimatePresence mode="wait">
          <motion.p
            key={translation}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            transition={{ duration: 0.2 }}
            className="flex-1 text-2xl font-medium leading-relaxed text-slate-900 dark:text-white"
          >
            {translation || (
              <span className="text-primary-200 dark:text-primary-800/50 italic">
                Translation will appear here
              </span>
            )}
          </motion.p>
        </AnimatePresence>
      </div>
    </div>
  );
};

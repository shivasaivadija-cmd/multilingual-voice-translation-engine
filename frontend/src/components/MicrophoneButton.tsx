import React from 'react';
import { motion } from 'framer-motion';
import { Mic, Square } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface MicrophoneButtonProps {
  isListening: boolean;
  onClick: () => void;
  className?: string;
  disabled?: boolean;
}

export const MicrophoneButton: React.FC<MicrophoneButtonProps> = ({ 
  isListening, 
  onClick, 
  className,
  disabled = false
}) => {
  return (
    <div className={twMerge("relative flex items-center justify-center", className)}>
      {isListening && (
        <div className="absolute inset-0 rounded-full animate-pulse-ring pointer-events-none" />
      )}
      <motion.button
        whileHover={{ scale: disabled ? 1 : 1.05 }}
        whileTap={{ scale: disabled ? 1 : 0.95 }}
        onClick={onClick}
        disabled={disabled}
        className={clsx(
          "relative z-10 flex h-20 w-20 items-center justify-center rounded-full text-white shadow-lg transition-all duration-300",
          disabled ? "bg-slate-400 cursor-not-allowed" :
          isListening 
            ? "bg-danger shadow-danger/50" 
            : "bg-primary-600 shadow-primary-600/50 hover:bg-primary-500"
        )}
      >
        <motion.div
          initial={false}
          animate={{ scale: isListening ? 1.2 : 1 }}
          transition={{ duration: 0.2 }}
        >
          {isListening ? <Square size={32} fill="currentColor" /> : <Mic size={32} />}
        </motion.div>
      </motion.button>
    </div>
  );
};

import React from 'react';
import { Settings, History, Globe2 } from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';

export const Header: React.FC = () => {
  const { connectionStatus } = useAppStore();

  return (
    <header className="sticky top-0 z-50 w-full backdrop-blur-md bg-white/70 dark:bg-slate-900/80 border-b border-slate-200/50 dark:border-slate-800/50">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 text-white shadow-lg shadow-primary-500/30">
            <Globe2 size={24} />
          </div>
          <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-900 to-slate-600 dark:from-white dark:to-slate-400 hidden sm:block">
            Voice Translator Pro
          </h1>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-800 text-sm font-medium">
            <span className="relative flex h-2.5 w-2.5">
              {connectionStatus === 'connected' && (
                <>
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                </>
              )}
              {connectionStatus === 'connecting' && (
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
              )}
              {connectionStatus === 'disconnected' && (
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
              )}
            </span>
            <span className="capitalize text-slate-600 dark:text-slate-300 hidden sm:inline-block">
              {connectionStatus}
            </span>
          </div>

          <button className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 transition-colors">
            <History size={20} />
          </button>
          
          <button className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 transition-colors">
            <Settings size={20} />
          </button>
        </div>
      </div>
    </header>
  );
};

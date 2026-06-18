import React from 'react';
import { motion } from 'framer-motion';

interface AudioVisualizerProps {
  level: number;
  isActive: boolean;
}

export const AudioVisualizer: React.FC<AudioVisualizerProps> = ({ level, isActive }) => {
  const bars = Array.from({ length: 24 }).map((_, i) => {
    const centerFactor = 1 - Math.abs(12 - i) / 12;
    return isActive ? Math.max(10, 10 + level * 80 * centerFactor) : 4;
  });

  return (
    <div className="flex items-center justify-center gap-1 h-24 w-full">
      {bars.map((height, index) => (
        <motion.div
          key={index}
          className="w-2 rounded-full bg-primary-500"
          animate={{ height: `${height}px` }}
          transition={{ type: 'tween', duration: 0.05 }}
          style={{
            opacity: isActive ? 0.6 + (level * 0.4) : 0.2,
            backgroundColor: isActive ? 'var(--color-primary-500)' : 'var(--color-primary-300)'
          }}
        />
      ))}
    </div>
  );
};

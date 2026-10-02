import React from 'react';
import { VoiceState } from '@/contexts/AssistantContext';

interface VoiceWaveformProps {
  state: VoiceState;
  className?: string;
}

export const VoiceWaveform: React.FC<VoiceWaveformProps> = ({ state, className = '' }) => {
  // 16 restrained technical audio bars
  const bars = [4, 6, 8, 12, 16, 10, 14, 18, 15, 11, 16, 13, 9, 6, 4, 3];

  return (
    <div
      className={`h-7 flex items-center justify-center gap-[3px] px-3 select-none ${className}`}
      aria-label={`Voice status: ${state}`}
    >
      {bars.map((defaultHeight, idx) => {
        let height = 3;
        let animationClass = '';
        let opacity = '0.35';

        if (state === 'idle') {
          height = 3;
          opacity = '0.3';
        } else if (state === 'listening') {
          height = Math.max(4, Math.round(defaultHeight * 1.1));
          animationClass = 'animate-pulse';
          opacity = '0.9';
        } else if (state === 'thinking') {
          height = (idx % 4) * 3 + 4;
          animationClass = 'animate-pulse';
          opacity = '0.7';
        } else if (state === 'generating') {
          height = (idx % 3) * 4 + 4;
          animationClass = 'animate-pulse';
          opacity = '0.8';
        } else if (state === 'playing') {
          height = defaultHeight;
          animationClass = 'animate-pulse';
          opacity = '0.95';
        } else if (state === 'paused') {
          height = Math.round(defaultHeight * 0.7);
          opacity = '0.5';
        } else if (state === 'error') {
          height = 2;
          opacity = '0.2';
        }

        // Sequential delay for fluid technical motion
        const delayMs = (idx * 60) % 600;

        return (
          <span
            key={idx}
            className={`w-[2.5px] rounded-full bg-[#1B2A4A] transition-all duration-200 ${animationClass}`}
            style={{
              height: `${height}px`,
              opacity,
              animationDelay: state !== 'idle' && state !== 'paused' ? `${delayMs}ms` : undefined,
              animationDuration: state === 'thinking' ? '1200ms' : state === 'listening' ? '600ms' : '800ms',
            }}
          />
        );
      })}
    </div>
  );
};

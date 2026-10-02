import React, { useEffect, useState } from 'react';
import { FileText, MessageSquare, Briefcase, TrendingUp } from 'lucide-react';
import { MetricData } from '@/types/dashboard';

interface MetricCardProps {
  data: MetricData;
  delay?: number;
}

export const MetricCard: React.FC<MetricCardProps> = ({ data, delay = 0 }) => {
  const [displayValue, setDisplayValue] = useState(0);

  // Smooth subtle count-up animation on initial load
  useEffect(() => {
    let start = 0;
    const end = data.value;
    if (start === end) {
      setDisplayValue(end);
      return;
    }

    const duration = 600;
    const stepTime = 20;
    const steps = Math.ceil(duration / stepTime);
    const increment = end / steps;

    const timer = setTimeout(() => {
      const interval = setInterval(() => {
        start += increment;
        if (start >= end) {
          setDisplayValue(end);
          clearInterval(interval);
        } else {
          setDisplayValue(Math.floor(start));
        }
      }, stepTime);

      return () => clearInterval(interval);
    }, delay);

    return () => clearTimeout(timer);
  }, [data.value, delay]);

  const getColors = () => {
    switch (data.color) {
      case 'blue':
        return {
          iconBg: 'bg-[#EFF6FF]',
          iconColor: 'text-[#2563EB]',
          strokeColor: '#3B82F6',
          fillId: 'blueGradient',
          stopColor: '#3B82F6',
        };
      case 'green':
        return {
          iconBg: 'bg-[#ECFDF5]',
          iconColor: 'text-[#059669]',
          strokeColor: '#10B981',
          fillId: 'greenGradient',
          stopColor: '#10B981',
        };
      case 'amber':
        return {
          iconBg: 'bg-[#FFFBEB]',
          iconColor: 'text-[#D97706]',
          strokeColor: '#F59E0B',
          fillId: 'amberGradient',
          stopColor: '#F59E0B',
        };
    }
  };

  const colors = getColors();

  const renderIcon = () => {
    switch (data.iconType) {
      case 'document':
        return <FileText size={18} className={colors.iconColor} />;
      case 'message':
        return <MessageSquare size={18} className={colors.iconColor} />;
      case 'briefcase':
        return <Briefcase size={18} className={colors.iconColor} />;
    }
  };

  // Unique wave shapes for subtle sparklines
  const getWavePath = () => {
    switch (data.color) {
      case 'blue':
        return {
          line: 'M0 28 C 30 18, 55 35, 85 20 C 115 5, 140 25, 170 14 C 200 4, 220 18, 260 8',
          area: 'M0 28 C 30 18, 55 35, 85 20 C 115 5, 140 25, 170 14 C 200 4, 220 18, 260 8 L 260 40 L 0 40 Z',
        };
      case 'green':
        return {
          line: 'M0 32 C 25 28, 50 34, 80 22 C 110 10, 135 30, 170 18 C 200 8, 230 14, 260 6',
          area: 'M0 32 C 25 28, 50 34, 80 22 C 110 10, 135 30, 170 18 C 200 8, 230 14, 260 6 L 260 40 L 0 40 Z',
        };
      case 'amber':
        return {
          line: 'M0 34 C 35 30, 65 36, 100 24 C 130 12, 165 32, 200 16 C 225 6, 245 10, 260 4',
          area: 'M0 34 C 35 30, 65 36, 100 24 C 130 12, 165 32, 200 16 C 225 6, 245 10, 260 4 L 260 40 L 0 40 Z',
        };
    }
  };

  const wave = getWavePath();

  return (
    <div className="relative overflow-hidden rounded-2xl bg-white border border-[#E2E2E2] p-5.5 flex flex-col justify-between hover:border-[#CBD5E1] hover:shadow-sm transition-all duration-200">
      {/* Top row: Icon & Trend */}
      <div className="flex items-start justify-between">
        <div className={`w-10 h-10 rounded-xl ${colors.iconBg} flex items-center justify-center`}>
          {renderIcon()}
        </div>

        <div className="flex items-center gap-1 text-[12px] font-semibold text-[#059669]">
          <TrendingUp size={13} />
          <span>{data.trend}</span>
          <span className="text-[11px] font-normal text-[#9CA3AF] ml-0.5">vs last month</span>
        </div>
      </div>

      {/* Center: Number & Title */}
      <div className="mt-4 mb-2 z-10">
        <div className="text-[32px] font-bold text-[#1A1A1A] leading-none tracking-tight">
          {displayValue}
        </div>
        <p className="text-[13px] font-medium text-[#6B6B6B] mt-1.5">
          {data.title}
        </p>
      </div>

      {/* Subtle sparkline at bottom */}
      <div className="absolute bottom-0 left-0 right-0 h-11 pointer-events-none opacity-85">
        <svg
          viewBox="0 0 260 40"
          className="w-full h-full preserve-3d"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id={colors.fillId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={colors.stopColor} stopOpacity="0.25" />
              <stop offset="100%" stopColor={colors.stopColor} stopOpacity="0.0" />
            </linearGradient>
          </defs>
          <path d={wave.area} fill={`url(#${colors.fillId})`} />
          <path
            d={wave.line}
            fill="none"
            stroke={colors.strokeColor}
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      </div>
    </div>
  );
};

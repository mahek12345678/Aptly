import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

interface JobMatchCardProps {
  matchCount?: number;
}

export const JobMatchCard: React.FC<JobMatchCardProps> = ({ matchCount = 0 }) => {
  const navigate = useNavigate();

  const hasMatches = typeof matchCount === 'number' && matchCount > 0;

  return (
    <div className="rounded-2xl bg-[#F0F4FA] border border-[#E2E8F0] p-5 sm:p-5.5 flex flex-col sm:flex-row items-center gap-4.5 shadow-2xs hover:border-[#CBD5E1] transition-all duration-200">
      {/* 3D Robot Assistant Vector */}
      <div className="w-18 h-18 sm:w-20 sm:h-20 shrink-0 relative flex items-center justify-center">
        <svg
          viewBox="0 0 100 100"
          className="w-full h-full drop-shadow-sm"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Head base */}
          <circle cx="50" cy="48" r="32" fill="#FFFFFF" stroke="#D1D5DB" strokeWidth="2" />
          
          {/* Head screen */}
          <rect
            x="28"
            y="32"
            width="44"
            height="30"
            rx="12"
            fill="#1E293B"
          />
          
          {/* Smiling Eyes */}
          <path
            d="M37 46 Q42 41 47 46"
            stroke="#60A5FA"
            strokeWidth="3"
            strokeLinecap="round"
            fill="none"
          />
          <path
            d="M53 46 Q58 41 63 46"
            stroke="#60A5FA"
            strokeWidth="3"
            strokeLinecap="round"
            fill="none"
          />

          {/* Ears / Side nodules */}
          <rect x="14" y="42" width="6" height="12" rx="3" fill="#94A3B8" />
          <rect x="80" y="42" width="6" height="12" rx="3" fill="#94A3B8" />

          {/* Head antenna */}
          <line x1="50" y1="16" x2="50" y2="8" stroke="#94A3B8" strokeWidth="3" strokeLinecap="round" />
          <circle cx="50" cy="7" r="4" fill="#3B82F6" />

          {/* Body */}
          <path
            d="M34 80 C34 72 40 68 50 68 C60 68 66 72 66 80 L68 88 C68 91 65 93 62 93 L38 93 C35 93 32 91 32 88 Z"
            fill="#E2E8F0"
            stroke="#CBD5E1"
            strokeWidth="1.5"
          />
          {/* Chest emblem */}
          <circle cx="50" cy="78" r="4" fill="#3B82F6" />
        </svg>
      </div>

      {/* Content & Action */}
      <div className="flex-1 text-center sm:text-left">
        <h4 className="font-serif text-[15px] sm:text-[15.5px] font-bold text-[#1E293B] leading-snug">
          {hasMatches
            ? `${matchCount} new position${matchCount === 1 ? '' : 's'} match your profile.`
            : 'Your personalized matches will appear here.'}
        </h4>
        <p className="text-[12px] text-[#64748B] mt-1 leading-relaxed">
          {hasMatches
            ? 'Deterministic AI ranking matched these against your resume vectors and preferences.'
            : 'We’re indexing new opportunities aligned with your resume and copilot preferences.'}
        </p>

        <button
          type="button"
          onClick={() => navigate('/find-positions')}
          className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#1B2A4A] hover:bg-[#142038] text-white text-[12.5px] font-semibold transition-all duration-180 shadow-xs hover:shadow-sm cursor-pointer"
        >
          <span>Explore New Jobs</span>
          <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
};

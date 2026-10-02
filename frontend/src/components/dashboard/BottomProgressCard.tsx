import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

interface BottomProgressCardProps {
  jobsApplied?: number;
}

export const BottomProgressCard: React.FC<BottomProgressCardProps> = ({ jobsApplied = 0 }) => {
  const navigate = useNavigate();

  return (
    <div className="rounded-2xl bg-white border border-[#E2E2E2] p-4 sm:p-5 flex flex-col md:flex-row items-center justify-between gap-4 shadow-2xs hover:border-[#CBD5E1] transition-all duration-200">
      {/* Left: Mountain Vector Illustration & Text */}
      <div className="flex flex-col sm:flex-row items-center gap-4 text-center sm:text-left">
        {/* Mountain SVG graphic */}
        <div className="w-24 h-16 shrink-0 relative flex items-center justify-center">
          <svg
            viewBox="0 0 120 70"
            className="w-full h-full"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Soft cloud background */}
            <path
              d="M10 35 C10 30 18 28 22 30 C25 24 35 24 38 29 C44 26 50 31 50 35 Z"
              fill="#E0E7FF"
              opacity="0.6"
            />
            {/* Left smaller mountain */}
            <polygon points="10,65 35,32 60,65" fill="#94A3B8" />
            <polygon points="35,32 42,42 28,42" fill="#E2E8F0" />

            {/* Right main mountain */}
            <polygon points="35,65 70,18 105,65" fill="#334155" />
            <polygon points="70,18 80,32 60,32" fill="#F1F5F9" />

            {/* Flag on the mountain peak */}
            <line
              x1="70"
              y1="18"
              x2="70"
              y2="8"
              stroke="#0F172A"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <polygon points="70,8 86,13 70,18" fill="#1B2A4A" />
          </svg>
        </div>

        {/* Text */}
        <div>
          <h4 className="font-serif text-[17px] font-bold text-[#1A1A1A]">
            {jobsApplied > 0 ? "Progress looks good!" : "Ready to start applying?"}
          </h4>
          <p className="text-[12.5px] text-[#6B6B6B] mt-0.5 leading-relaxed">
            {jobsApplied > 0
              ? `You've applied to ${jobsApplied} ${jobsApplied === 1 ? 'job' : 'jobs'}. Keep the momentum going!`
              : "Track your job applications to monitor your progress and unlock tailored AI insights."}
          </p>
        </div>
      </div>

      {/* Right: CTA Button */}
      <button
        type="button"
        onClick={() => navigate('/track-jobs')}
        className="shrink-0 inline-flex items-center gap-2 px-4.5 py-2 rounded-xl bg-white hover:bg-[#F8FAFC] border border-[#CBD5E1] text-[#1B2A4A] text-[13px] font-semibold transition-all duration-180 shadow-2xs hover:shadow-xs group"
      >
        <span>Track Jobs</span>
        <ArrowRight
          size={14}
          className="group-hover:translate-x-0.5 transition-transform"
        />
      </button>
    </div>
  );
};

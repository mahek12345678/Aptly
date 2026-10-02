import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, FileText, BarChart2 } from 'lucide-react';

export const QuickActions: React.FC = () => {
  const navigate = useNavigate();

  const actions = [
    {
      label: 'Find New Positions',
      icon: Search,
      onClick: () => navigate('/find-positions'),
    },
    {
      label: 'Analyze a JD',
      icon: FileText,
      onClick: () => navigate('/jd-analyzer'),
    },
    {
      label: 'View Tracked Jobs',
      icon: BarChart2,
      onClick: () => navigate('/track-jobs'),
    },
  ];

  return (
    <div className="rounded-2xl bg-white border border-[#E2E2E2] p-5.5 sm:p-6 shadow-2xs">
      <h3 className="font-serif text-[18px] font-bold text-[#1A1A1A] tracking-tight mb-3.5">
        Quick Actions
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        {actions.map((act) => {
          const Icon = act.icon;
          return (
            <button
              key={act.label}
              type="button"
              onClick={act.onClick}
              className="flex items-center gap-2.5 p-3 rounded-xl bg-[#F8FAFC] hover:bg-[#EFF6FF] border border-[#E2E8F0] hover:border-[#BFDBFE] text-left transition-all duration-180 group cursor-pointer"
            >
              <div className="w-7 h-7 rounded-lg bg-white shadow-2xs border border-[#E2E8F0] flex items-center justify-center shrink-0 group-hover:border-[#93C5FD]">
                <Icon
                  size={14}
                  className="text-[#2563EB] group-hover:scale-110 transition-transform"
                />
              </div>
              <span className="text-[12.5px] font-semibold text-[#1E293B] group-hover:text-[#1B2A4A] truncate">
                {act.label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

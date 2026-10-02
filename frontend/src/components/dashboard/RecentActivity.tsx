import React from 'react';
import { useNavigate } from 'react-router-dom';
import { RecentActivityItem } from '@/types/dashboard';

interface RecentActivityProps {
  items?: RecentActivityItem[];
}

export const RecentActivity: React.FC<RecentActivityProps> = ({ items = [] }) => {
  const navigate = useNavigate();

  const formatActionText = (item: RecentActivityItem) => {
    const raw = (item.status || '').toLowerCase();
    if (raw.includes('applied')) {
      return `Applied to ${item.company}`;
    }
    if (raw.includes('oa') || raw.includes('assessment')) {
      return `Moved to OA for ${item.company}`;
    }
    if (raw.includes('interview')) {
      return `Interview scheduled with ${item.company}`;
    }
    if (raw.includes('offer')) {
      return `Offer received from ${item.company}`;
    }
    if (raw.includes('reject')) {
      return `Decision received from ${item.company}`;
    }
    return `${item.status} · ${item.company}`;
  };

  return (
    <div className="rounded-lg border border-[#E2E2E2] bg-white p-5 sm:p-6 shadow-2xs flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 border-b border-[#F0F0F0]">
        <h3 className="font-serif text-[18px] font-bold text-[#1A1A1A] tracking-tight">
          Recent Activity
        </h3>
        <span className="font-mono text-[9.5px] text-[#8E8E93] bg-[#F5F5F7] border border-[#E5E5EA] px-2 py-0.5 rounded tracking-wider font-semibold uppercase">
          AUDIT TRAIL
        </span>
      </div>

      {/* Ledger Rows */}
      {items.length === 0 ? (
        <div className="py-8 text-center text-[12px] text-[#6B6B6B]">
          No recent activity recorded in the audit trail.
        </div>
      ) : (
        <div className="divide-y divide-[#F0F0F0]">
          {items.slice(0, 5).map((item) => (
            <div
              key={item.id}
              onClick={() => navigate('/track-jobs')}
              className="py-3 flex items-center justify-between gap-3 text-[13px] hover:bg-[#FAFBFD] -mx-2 px-2 rounded transition-colors duration-180 cursor-pointer group"
            >
              <span className="font-medium text-[#1A1A1A] group-hover:text-[#1B2A4A] transition-colors truncate">
                {formatActionText(item)}
              </span>
              <span className="font-mono text-[11px] text-[#8E8E93] shrink-0">
                {item.updatedAt}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

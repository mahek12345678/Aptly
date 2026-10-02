import React, { useMemo } from 'react';
import { ArrowUpRight } from 'lucide-react';

interface DashboardMetricsStripProps {
  jobsApplied: number;
  repliesReceived: number;
  offersReceived: number;
  thisWeekCount?: number;
}

export const DashboardMetricsStrip: React.FC<DashboardMetricsStripProps> = ({
  jobsApplied,
  repliesReceived,
  offersReceived,
  thisWeekCount = 0,
}) => {
  // Conversion rate derived from real data
  const conversionRate = useMemo(() => {
    if (jobsApplied <= 0) return '0.0%';
    const pct = (repliesReceived / jobsApplied) * 100;
    return `${pct.toFixed(1)}%`;
  }, [jobsApplied, repliesReceived]);

  return (
    <div className="rounded-lg border border-[#E2E2E2] bg-white grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-[#E2E2E2] shadow-2xs overflow-hidden">
      {/* 1. PIPELINE VOLUME */}
      <div className="p-5 sm:p-6 flex flex-col justify-between space-y-3.5">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10.5px] uppercase tracking-wider text-[#6B6B6B] font-semibold">
            PIPELINE VOLUME
          </span>
          <span className="font-mono text-[9.5px] text-[#8E8E93] bg-[#F5F5F7] border border-[#E5E5EA] px-1.5 py-0.5 rounded tracking-wide font-medium">
            STAGE 1
          </span>
        </div>

        <div className="flex items-baseline gap-2.5">
          <span className="font-serif text-[32px] sm:text-[38px] font-bold text-[#1A1A1A] tracking-tight leading-none">
            {jobsApplied}
          </span>
          <span className="text-[13.5px] font-medium text-[#1A1A1A]">
            {jobsApplied === 1 ? 'Job Applied' : 'Jobs Applied'}
          </span>
        </div>

        <div className="flex items-center gap-1 text-[11.5px] text-[#6B6B6B]">
          {thisWeekCount > 0 ? (
            <span className="inline-flex items-center gap-0.5 text-[#1B2A4A] font-medium">
              <ArrowUpRight size={13} className="text-[#1B2A4A]" />
              <span>+{thisWeekCount} this week</span>
            </span>
          ) : (
            <span>Active pipeline tracking</span>
          )}
        </div>
      </div>

      {/* 2. RESPONSE RATE */}
      <div className="p-5 sm:p-6 flex flex-col justify-between space-y-3.5">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10.5px] uppercase tracking-wider text-[#6B6B6B] font-semibold">
            RESPONSE RATE
          </span>
          <span className="font-mono text-[9.5px] text-[#8E8E93] bg-[#F5F5F7] border border-[#E5E5EA] px-1.5 py-0.5 rounded tracking-wide font-medium">
            STAGE 2
          </span>
        </div>

        <div className="flex items-baseline gap-2.5">
          <span className="font-serif text-[32px] sm:text-[38px] font-bold text-[#1A1A1A] tracking-tight leading-none">
            {repliesReceived}
          </span>
          <span className="text-[13.5px] font-medium text-[#1A1A1A]">
            Replies Received
          </span>
        </div>

        <div className="text-[11.5px] text-[#6B6B6B]">
          <span>{conversionRate} direct conversion</span>
        </div>
      </div>

      {/* 3. FINAL STAGE */}
      <div className="p-5 sm:p-6 flex flex-col justify-between space-y-3.5">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10.5px] uppercase tracking-wider text-[#6B6B6B] font-semibold">
            FINAL STAGE
          </span>
          <span className="font-mono text-[9.5px] text-[#8E8E93] bg-[#F5F5F7] border border-[#E5E5EA] px-1.5 py-0.5 rounded tracking-wide font-medium">
            STAGE 3
          </span>
        </div>

        <div className="flex items-baseline gap-2.5">
          <span className="font-serif text-[32px] sm:text-[38px] font-bold text-[#1A1A1A] tracking-tight leading-none">
            {offersReceived}
          </span>
          <span className="text-[13.5px] font-medium text-[#1A1A1A]">
            Offers Received
          </span>
        </div>

        <div className="text-[11.5px] text-[#6B6B6B]">
          {offersReceived > 0 ? (
            <span className="text-[#1E4D3A] font-medium">Decision window open</span>
          ) : (
            <span>0 pending decisions</span>
          )}
        </div>
      </div>
    </div>
  );
};

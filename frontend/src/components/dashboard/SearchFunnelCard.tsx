import React, { useMemo, useState } from 'react';
import { Filter, Info } from 'lucide-react';
import { JobApplication } from '@/types/application';

interface SearchFunnelCardProps {
  applications: JobApplication[];
}

interface FunnelStage {
  id: string;
  name: string;
  count: number;
  percentage: number;
  unit: string;
  color: string;
  description: string;
}

export const SearchFunnelCard: React.FC<SearchFunnelCardProps> = ({
  applications,
}) => {
  const [hoveredStage, setHoveredStage] = useState<string | null>(null);

  // Compute funnel metrics strictly from canonical real application statuses
  const stages: FunnelStage[] = useMemo(() => {
    const totalApplied = applications.length;

    // Applications that reached Screened / OA or beyond
    const screenedCount = applications.filter((a) =>
      ['oa', 'interview', 'offer'].includes(a.status?.toLowerCase() || '')
    ).length;

    // Applications that reached Interviews or beyond
    const interviewCount = applications.filter((a) =>
      ['interview', 'offer'].includes(a.status?.toLowerCase() || '')
    ).length;

    // Applications that reached Offers
    const offerCount = applications.filter(
      (a) => a.status?.toLowerCase() === 'offer'
    ).length;

    const calcPct = (count: number) => {
      if (totalApplied === 0) return 0;
      return Number(((count / totalApplied) * 100).toFixed(1));
    };

    return [
      {
        id: 'applied',
        name: '1. Applied',
        count: totalApplied,
        percentage: totalApplied > 0 ? 100 : 0,
        unit: 'roles',
        color: '#1B2A4A',
        description: 'Baseline submitted application volume',
      },
      {
        id: 'oa',
        name: '2. Screened / OA',
        count: screenedCount,
        percentage: calcPct(screenedCount),
        unit: 'roles',
        color: '#3D5580',
        description: 'Candidates advancing past initial resume screenings & assessments',
      },
      {
        id: 'interview',
        name: '3. Interviews',
        count: interviewCount,
        percentage: calcPct(interviewCount),
        unit: 'roles',
        color: '#6B82A6',
        description: 'Direct conversational interview rounds scheduled',
      },
      {
        id: 'offer',
        name: '4. Offers',
        count: offerCount,
        percentage: calcPct(offerCount),
        unit: offerCount === 1 ? 'offer' : 'offers',
        color: '#1E4D3A',
        description: 'Final stage job offers received and in negotiation',
      },
    ];
  }, [applications]);

  const activeDescription = useMemo(() => {
    if (!hoveredStage) {
      return 'Hover over each funnel tier for milestone conversion insights...';
    }
    const match = stages.find((s) => s.id === hoveredStage);
    return match ? `${match.name}: ${match.description}` : '';
  }, [hoveredStage, stages]);

  return (
    <div className="rounded-lg border border-[#E2E2E2] bg-white p-5 sm:p-6 shadow-2xs flex flex-col justify-between h-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-[#F0F0F0]">
        <h3 className="font-serif text-[18px] font-bold text-[#1A1A1A] tracking-tight flex items-center gap-2">
          <Filter size={16} className="text-[#1B2A4A]" />
          <span>Search Funnel Drop-off</span>
        </h3>
        <span className="font-mono text-[9.5px] text-[#8E8E93] bg-[#F5F5F7] border border-[#E5E5EA] px-2 py-0.5 rounded tracking-wider font-semibold uppercase">
          4 STAGES
        </span>
      </div>

      {/* 4 Stages Rails */}
      <div className="py-4 space-y-4">
        {stages.map((stage) => (
          <div
            key={stage.id}
            onMouseEnter={() => setHoveredStage(stage.id)}
            onMouseLeave={() => setHoveredStage(null)}
            className="group cursor-default"
          >
            <div className="flex items-center justify-between text-[12.5px] mb-1.5">
              <span className="font-medium text-[#1A1A1A] group-hover:text-[#1B2A4A] transition-colors flex items-center gap-1.5">
                <span
                  className="w-1.5 h-1.5 rounded-full inline-block"
                  style={{ backgroundColor: stage.color }}
                />
                <span>{stage.name}</span>
              </span>
              <span className="font-mono text-[11.5px] text-[#6B6B6B]">
                <strong className="font-semibold text-[#1A1A1A]">
                  {stage.count} {stage.unit}
                </strong>{' '}
                ({stage.percentage}%)
              </span>
            </div>

            {/* Progress rail */}
            <div className="w-full h-2 rounded-xs bg-[#F0F0F0] overflow-hidden">
              <div
                className="h-full rounded-xs transition-all duration-300 ease-out"
                style={{
                  width: `${Math.max(stage.percentage, stage.count > 0 ? 3 : 0)}%`,
                  backgroundColor: stage.color,
                }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Bottom Insights Callout */}
      <div className="pt-3 border-t border-[#F0F0F0]">
        <div className="rounded border border-[#E8E8E8] bg-[#FAFAFA] p-2.5 flex items-start gap-2 text-[11px] text-[#6B6B6B] leading-relaxed">
          <Info size={13} className="text-[#6B6B6B] shrink-0 mt-0.5" />
          <span className="truncate">{activeDescription}</span>
        </div>
      </div>
    </div>
  );
};

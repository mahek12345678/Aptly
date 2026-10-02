import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { JobMatchesListResponse, JobMatchItem } from '@/types/jobs';

interface DashboardMatchesLedgerProps {
  totalMatchesCount?: number;
}

export const DashboardMatchesLedger: React.FC<DashboardMatchesLedgerProps> = ({
  totalMatchesCount,
}) => {
  const navigate = useNavigate();
  const [matches, setMatches] = useState<JobMatchItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(totalMatchesCount || 0);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    api
      .get<JobMatchesListResponse>('/api/v1/jobs/matches?limit=4')
      .then((res) => {
        if (!isMounted || !res) return;
        setMatches(res.items || []);
        if (typeof res.total === 'number') {
          setTotalCount(res.total);
        }
        if (res.last_refreshed_at) {
          setLastRefreshedAt(res.last_refreshed_at);
        }
      })
      .catch((err) => {
        console.error('Failed to load top matches for dashboard:', err);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Update total count if prop changes
  useEffect(() => {
    if (typeof totalMatchesCount === 'number') {
      setTotalCount(totalMatchesCount);
    }
  }, [totalMatchesCount]);

  // Relative updated string
  const formattedUpdated = useMemo(() => {
    if (!lastRefreshedAt) return 'Updated recently';
    try {
      const dt = new Date(lastRefreshedAt);
      const diffMin = Math.round((Date.now() - dt.getTime()) / (1000 * 60));
      if (diffMin < 2) return 'Updated just now';
      if (diffMin < 60) return `Updated ${diffMin}m ago`;
      const diffHours = Math.round(diffMin / 60);
      if (diffHours < 24) return `Updated ${diffHours}h ago`;
      return `Updated yesterday`;
    } catch {
      return 'Updated recently';
    }
  }, [lastRefreshedAt]);

  return (
    <div className="rounded-lg border border-[#E2E2E2] bg-white p-5 sm:p-6 shadow-2xs flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 border-b border-[#F0F0F0]">
        <h3 className="font-serif text-[18px] font-bold text-[#1A1A1A] tracking-tight">
          Your Matches
        </h3>
        <span className="font-mono text-[9.5px] text-[#8E8E93] bg-[#F5F5F7] border border-[#E5E5EA] px-2 py-0.5 rounded tracking-wider font-semibold uppercase">
          AI VECTOR INDEX
        </span>
      </div>

      {/* Rows */}
      {isLoading ? (
        <div className="py-8 text-center text-[12px] text-[#8E8E93] font-mono">
          Querying semantic vector index...
        </div>
      ) : matches.length === 0 ? (
        <div className="py-8 text-center">
          <p className="text-[12.5px] font-medium text-[#1A1A1A]">
            No vector matches generated yet
          </p>
          <p className="text-[11.5px] text-[#6B6B6B] mt-0.5">
            Upload your resume or discover open positions in Find New Positions.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-[#F0F0F0]">
          {matches.slice(0, 3).map((match) => {
            const score =
              match.final_score <= 1.0
                ? Math.round(match.final_score * 100)
                : Math.round(match.final_score);

            const locationStr = match.job.location || 'Remote / Hybrid';
            const empType = match.job.employment_type
              ? ` · ${match.job.employment_type}`
              : '';

            return (
              <div
                key={match.id}
                onClick={() => navigate('/find-positions')}
                className="py-3 flex items-center justify-between gap-3 text-[13px] hover:bg-[#FAFBFD] -mx-2 px-2 rounded transition-colors duration-180 cursor-pointer group"
              >
                {/* Left: Company & Details */}
                <div className="min-w-0 pr-2">
                  <h4 className="font-bold text-[#1A1A1A] group-hover:text-[#1B2A4A] transition-colors truncate">
                    {match.job.company}
                  </h4>
                  <p className="text-[12px] text-[#6B6B6B] truncate mt-0.5">
                    {match.job.role_title} · {locationStr}
                    {empType}
                  </p>
                </div>

                {/* Right: Score + Mini Horizontal Meter */}
                <div className="flex flex-col items-end shrink-0 space-y-1">
                  <span className="font-mono text-[12px] font-semibold text-[#1A1A1A]">
                    {score}% match
                  </span>
                  <div className="w-16 h-1 rounded-full bg-[#E5E7EB] overflow-hidden">
                    <div
                      className="h-full rounded-full bg-[#1B2A4A] transition-all duration-300"
                      style={{ width: `${Math.min(score, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Footer Link & Timestamp */}
      <div className="pt-3 border-t border-[#F0F0F0] flex items-center justify-between text-[11.5px]">
        <button
          type="button"
          onClick={() => navigate('/find-positions')}
          className="font-medium text-[#1B2A4A] hover:text-[#253961] hover:underline transition-all cursor-pointer inline-flex items-center gap-1"
        >
          <span>View all {totalCount > 0 ? totalCount : ''} matches</span>
          <span>→</span>
        </button>
        <span className="text-[#8E8E93] font-mono text-[10.5px]">
          {formattedUpdated}
        </span>
      </div>
    </div>
  );
};

import React from 'react';
import { JobMatchItem } from '@/types/jobs';
import { extractJobIntelligence } from '@/lib/jobPresentation';

interface JobLedgerRowProps {
  match: JobMatchItem;
  rank: number;
  isSelected: boolean;
  onSelect: (match: JobMatchItem) => void;
}

export const JobLedgerRow: React.FC<JobLedgerRowProps> = ({
  match,
  rank,
  isSelected,
  onSelect,
}) => {
  const { job } = match;

  // Format ranking with leading zero if single digit (e.g. #01 or #1)
  const rankDisplay = rank < 10 ? `#${rank}` : `#${rank}`;

  // Time format helper
  const formatPostedTime = (isoString?: string | null) => {
    if (!isoString) return null;
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return null;
    const diffMin = Math.floor((Date.now() - date.getTime()) / 60000);
    if (diffMin < 1) return 'Posted just now';
    if (diffMin < 60) return `Posted ${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `Posted ${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return 'Posted yesterday';
    if (diffDays < 7) return `Posted ${diffDays}d ago`;
    return `Posted ${date.toLocaleDateString()}`;
  };

  const postedText = formatPostedTime(job.posted_at);
  const isLiveProvider = job.source && job.source.toLowerCase() !== 'mock';

  // Extract 2-3 strongest skills
  const intelligence = extractJobIntelligence(
    job.description,
    match.match_reasons,
    job.role_title,
    job.company,
    job.location,
    job.employment_type
  );
  const displaySkills = intelligence.matchedSkills.slice(0, 3);

  // Meta line elements (Location / work mode · Compensation)
  const metaParts: string[] = [];
  if (job.location) {
    metaParts.push(job.location);
  }
  if (job.compensation && job.compensation.trim()) {
    metaParts.push(job.compensation.trim());
  }
  const metaLine = metaParts.join(' · ');

  return (
    <div
      onClick={() => onSelect(match)}
      className={`group relative text-left p-4 cursor-pointer transition-all duration-150 border-b border-[#E2E2E2] ${
        isSelected
          ? 'bg-[#EBF3FA] border-l-2 border-l-[#1B2A4A] pl-[14px]'
          : 'bg-white hover:bg-slate-50/70 hover:translate-x-0.5 border-l-2 border-l-transparent'
      }`}
    >
      {/* Top Row: Ranking & Company on Left, Match % Badge on Right */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="font-mono text-xs font-semibold text-[#1B2A4A]">
            {rankDisplay}
          </span>
          <span className="font-semibold text-xs text-[#1A1A1A] truncate">
            {job.company}
          </span>
          {isLiveProvider && (
            <span className="px-1.5 py-0.2 rounded text-[9.5px] font-mono font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800">
              LIVE
            </span>
          )}
        </div>

        <div className="shrink-0">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-[#EAF5F0] text-[#1E7E51] border border-[#CDE7DC]">
            {Math.round(match.final_score)}% Match
          </span>
        </div>
      </div>

      {/* Role Title */}
      <h3 className="text-[13.5px] font-semibold text-[#1A1A1A] mt-1 tracking-tight truncate">
        {job.role_title}
      </h3>

      {/* Meta Line: Location · Compensation */}
      {metaLine && (
        <p className="text-[11.5px] text-[#6B6B6B] mt-0.5 truncate">
          {metaLine}
        </p>
      )}

      {/* Posted Time (if available) */}
      {postedText && (
        <p className="text-[10.5px] text-[#9CA3AF] mt-0.5">
          {postedText}
        </p>
      )}

      {/* Strongest Matching Skills Pills */}
      {displaySkills.length > 0 && (
        <div className="flex items-center gap-1.5 mt-2.5 flex-wrap">
          {displaySkills.map((skill, idx) => (
            <span
              key={idx}
              className="px-2 py-0.5 rounded bg-[#F1F3F5] text-[#4A5568] text-[10.5px] font-medium"
            >
              {skill}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

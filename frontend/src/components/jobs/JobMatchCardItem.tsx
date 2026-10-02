import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MapPin,
  Briefcase,
  DollarSign,
  Bookmark,
  BookmarkCheck,
  EyeOff,
  CheckCircle2,
  FileSearch,
  PlusCircle,
  ExternalLink,
  ChevronRight,
} from 'lucide-react';
import { JobMatchItem } from '@/types/jobs';
import { api } from '@/lib/api';
import { startApplicationIntent } from '@/lib/applyIntent';

interface JobMatchCardItemProps {
  match: JobMatchItem;
  onOpenDetails: (match: JobMatchItem) => void;
  onToggleSave: (matchId: string) => Promise<void>;
  onDismiss: (matchId: string) => Promise<void>;
  onAddedToTracker?: (matchId: string) => void;
}

export const JobMatchCardItem: React.FC<JobMatchCardItemProps> = ({
  match,
  onOpenDetails,
  onToggleSave,
  onDismiss,
  onAddedToTracker,
}) => {
  const navigate = useNavigate();
  const [isAdding, setIsAdding] = useState(false);
  const [added, setAdded] = useState(false);

  const { job } = match;

  const scoreBadgeBg =
    match.final_score >= 80
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : match.final_score >= 60
      ? 'bg-blue-50 text-blue-700 border-blue-200'
      : 'bg-slate-50 text-slate-700 border-slate-200';

  const handleApplyClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await startApplicationIntent({
        company: job.company,
        role: job.role_title,
        location: job.location || 'Remote',
        deadline: job.deadline,
        compensation: job.compensation,
        job_description: job.description,
        application_url: job.application_url,
        source: 'Job Matching',
        source_job_id: job.id,
      });
    } catch (err) {
      console.error('Failed to start application:', err);
    }
  };

  const handleQuickAdd = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (added || isAdding) return;

    setIsAdding(true);
    try {
      await api.post('/api/v1/applications', {
        company: job.company,
        role: job.role_title,
        location: job.location || 'Remote',
        status: 'applied',
        deadline: job.deadline,
        stipend: job.compensation,
        job_description: job.description,
        source: 'Job Matching',
        source_job_id: job.id,
      });
      setAdded(true);
      if (onAddedToTracker) {
        onAddedToTracker(match.id);
      }
    } catch (err) {
      console.error('Failed to quick add to tracker:', err);
    } finally {
      setIsAdding(false);
    }
  };

  const handleAnalyzeClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigate('/jd-analyzer', {
      state: {
        jobDescription: job.description,
        description: job.description,
        roleTitle: job.role_title,
        role_title: job.role_title,
        company: job.company,
        applicationUrl: job.application_url,
        application_url: job.application_url,
        sourceJobId: job.id,
        source_job_id: job.id,
      },
    });
  };

  const handleSaveClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleSave(match.id);
  };

  const handleDismissClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDismiss(match.id);
  };

  return (
    <div
      onClick={() => onOpenDetails(match)}
      className="group relative rounded-2xl bg-white border border-[#E2E2E2] p-5 sm:p-6 shadow-2xs hover:shadow-sm hover:border-[#CBD5E1] transition-all duration-200 cursor-pointer flex flex-col justify-between"
    >
      <div>
        {/* Top Header: Company, Match Badge, Save & Dismiss */}
        <div className="flex items-start justify-between gap-3 mb-2.5">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${scoreBadgeBg}`}
            >
              {Math.round(match.final_score)}% Match
            </span>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              {job.company}
            </span>
          </div>

          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={handleSaveClick}
              title={match.saved ? 'Remove Bookmark' : 'Save Listing'}
              className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                match.saved
                  ? 'text-amber-600 bg-amber-50 hover:bg-amber-100'
                  : 'text-slate-400 hover:text-slate-700 hover:bg-slate-100'
              }`}
            >
              {match.saved ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}
            </button>

            <button
              type="button"
              onClick={handleDismissClick}
              title="Dismiss Match"
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <EyeOff size={16} />
            </button>
          </div>
        </div>

        {/* Role Title */}
        <h3 className="font-serif text-lg sm:text-xl font-bold text-[#1B2A4A] group-hover:text-blue-900 transition-colors leading-tight mb-3">
          {job.role_title}
        </h3>

        {/* Metadata Badges */}
        <div className="flex items-center gap-3 text-xs text-[#6B6B6B] flex-wrap mb-3.5">
          {job.location && (
            <span className="flex items-center gap-1 bg-slate-50 border border-slate-200/60 px-2 py-0.5 rounded-md">
              <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                <MapPin size={12} className="text-slate-400" aria-hidden="true" focusable="false" />
              </span>
              <span>{job.location}</span>
            </span>
          )}
          {job.employment_type && (
            <span className="flex items-center gap-1 bg-slate-50 border border-slate-200/60 px-2 py-0.5 rounded-md capitalize">
              <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                <Briefcase size={12} className="text-slate-400" aria-hidden="true" focusable="false" />
              </span>
              <span>{job.employment_type.replace('_', ' ')}</span>
            </span>
          )}
          {job.compensation && (
            <span className="flex items-center gap-1 bg-slate-50 border border-slate-200/60 px-2 py-0.5 rounded-md">
              <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                <DollarSign size={12} className="text-slate-400" aria-hidden="true" focusable="false" />
              </span>
              <span>{job.compensation}</span>
            </span>
          )}
        </div>

        {/* Grounded Match Reasons */}
        {match.match_reasons && match.match_reasons.length > 0 && (
          <div className="space-y-1 mb-4">
            {match.match_reasons.slice(0, 2).map((reason, idx) => (
              <div key={idx} className="flex items-center gap-1.5 text-xs text-slate-700 leading-tight">
                <CheckCircle2 size={13} className="text-emerald-600 shrink-0" />
                <span className="truncate">{reason}</span>
              </div>
            ))}
          </div>
        )}

        {/* Short JD preview */}
        <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed mb-4">
          {job.description}
        </p>
      </div>

      {/* Card Actions Footer */}
      <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={handleAnalyzeClick}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-blue-900 transition-colors cursor-pointer"
        >
          <FileSearch size={14} className="text-blue-600" />
          <span>Tailor Resume</span>
        </button>

        <div className="flex items-center gap-2">
          {job.application_url ? (
            <button
              type="button"
              onClick={handleApplyClick}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#1B2A4A] hover:bg-[#142038] text-white text-xs font-semibold shadow-2xs transition-all cursor-pointer active:scale-95"
            >
              <span>Apply</span>
              <ExternalLink size={12} />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleQuickAdd}
              disabled={added || isAdding}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                added
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 cursor-default'
                  : 'bg-white border border-slate-200 hover:bg-slate-50 text-slate-800'
              }`}
            >
              {added ? (
                <>
                  <CheckCircle2 size={13} className="text-emerald-600" />
                  <span>Tracked</span>
                </>
              ) : (
                <>
                  <PlusCircle size={13} />
                  <span>{isAdding ? 'Adding...' : 'Track'}</span>
                </>
              )}
            </button>
          )}

          <span className="p-1 text-slate-400 group-hover:text-slate-700 transition-colors">
            <ChevronRight size={16} />
          </span>
        </div>
      </div>
    </div>
  );
};

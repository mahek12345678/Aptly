import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X,
  Bookmark,
  BookmarkCheck,
  EyeOff,
  ExternalLink,
  Briefcase,
  MapPin,
  DollarSign,
  Calendar,
  CheckCircle2,
  PlusCircle,
  FileSearch,
} from 'lucide-react';
import { JobMatchItem } from '@/types/jobs';
import { api } from '@/lib/api';
import { startApplicationIntent } from '@/lib/applyIntent';

interface JobMatchDetailModalProps {
  match: JobMatchItem | null;
  isOpen: boolean;
  onClose: () => void;
  onToggleSave: (matchId: string) => Promise<void>;
  onDismiss: (matchId: string) => Promise<void>;
  onAddedToTracker?: (matchId: string) => void;
}

export const JobMatchDetailModal: React.FC<JobMatchDetailModalProps> = ({
  match,
  isOpen,
  onClose,
  onToggleSave,
  onDismiss,
  onAddedToTracker,
}) => {
  const navigate = useNavigate();
  const [isApplying, setIsApplying] = useState(false);
  const [isAddingToTracker, setIsAddingToTracker] = useState(false);
  const [addedSuccess, setAddedSuccess] = useState(false);
  const [trackerError, setTrackerError] = useState<string | null>(null);

  if (!isOpen || !match) return null;

  const { job } = match;

  const scoreBadgeBg =
    match.final_score >= 80
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : match.final_score >= 60
      ? 'bg-blue-50 text-blue-700 border-blue-200'
      : 'bg-slate-50 text-slate-700 border-slate-200';

  const handleApply = async () => {
    setIsApplying(true);
    setTrackerError(null);
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
      onClose();
    } catch (err: any) {
      setTrackerError(err?.message || 'Could not start application. Please try again.');
    } finally {
      setIsApplying(false);
    }
  };

  const handleAddToTracker = async () => {
    setIsAddingToTracker(true);
    setTrackerError(null);
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
      setAddedSuccess(true);
      if (onAddedToTracker) {
        onAddedToTracker(match.id);
      }
    } catch (err: any) {
      setTrackerError(err?.message || 'Could not add to Track Jobs. Please try again.');
    } finally {
      setIsAddingToTracker(false);
    }
  };

  const handleAnalyzeResume = () => {
    onClose();
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

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/40 backdrop-blur-xs transition-opacity"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl border border-slate-200 shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in-50 zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-start justify-between gap-4 bg-slate-50/60">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${scoreBadgeBg}`}
              >
                {Math.round(match.final_score)}% Match
              </span>
              {job.employment_type && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 capitalize">
                  {job.employment_type.replace('_', ' ')}
                </span>
              )}
            </div>
            <h2 className="font-serif text-xl sm:text-2xl font-bold text-slate-900 leading-tight">
              {job.role_title}
            </h2>
            <p className="text-sm font-semibold text-slate-600">{job.company}</p>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors cursor-pointer"
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-sm text-slate-700">
          {/* Metadata Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3.5 rounded-xl bg-slate-50 border border-slate-150">
            <div className="flex items-center gap-2 text-xs text-slate-600">
              <MapPin size={15} className="text-slate-400 shrink-0" />
              <span className="truncate">{job.location || 'Not specified'}</span>
            </div>
            {job.compensation && (
              <div className="flex items-center gap-2 text-xs text-slate-600">
                <DollarSign size={15} className="text-slate-400 shrink-0" />
                <span className="truncate">{job.compensation}</span>
              </div>
            )}
            {job.deadline && (
              <div className="flex items-center gap-2 text-xs text-slate-600">
                <Calendar size={15} className="text-slate-400 shrink-0" />
                <span className="truncate">
                  Deadline: {new Date(job.deadline).toLocaleDateString()}
                </span>
              </div>
            )}
          </div>

          {/* Match Score & Evidence Breakdown */}
          <div className="p-4 rounded-xl bg-indigo-50/50 border border-indigo-100 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold text-indigo-950 uppercase tracking-wider">
                <FileSearch size={15} className="text-indigo-600" />
                <span>Deterministic Match Breakdown</span>
              </div>
              <span className="text-xs text-indigo-600 font-medium">
                70% Vector Sim + 30% Preference Fit
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-2.5 rounded-lg bg-white/80 border border-indigo-100/70">
                <span className="text-slate-500 block mb-0.5">Resume Vector Similarity</span>
                <span className="text-sm font-bold text-slate-900">
                  {Math.round(match.similarity_score)}%
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-white/80 border border-indigo-100/70">
                <span className="text-slate-500 block mb-0.5">Preference Alignment</span>
                <span className="text-sm font-bold text-slate-900">
                  {Math.round(match.preference_score)}%
                </span>
              </div>
            </div>

            {match.match_reasons && match.match_reasons.length > 0 && (
              <div className="pt-2 border-t border-indigo-100/70 space-y-1.5">
                <span className="text-xs font-semibold text-indigo-900 block">
                  Grounding Factors:
                </span>
                <ul className="space-y-1 text-xs text-slate-700">
                  {match.match_reasons.map((reason, idx) => (
                    <li key={idx} className="flex items-start gap-1.5 leading-relaxed">
                      <CheckCircle2 size={13} className="text-emerald-600 shrink-0 mt-0.5" />
                      <span>{reason}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Role Description */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                <Briefcase size={14} className="text-slate-400" aria-hidden="true" focusable="false" />
              </span>
              <span>Job Description</span>
            </h3>
            <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200 text-xs text-slate-700 leading-relaxed max-h-60 overflow-y-auto whitespace-pre-line font-normal">
              {job.description}
            </div>
          </div>

          {trackerError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">
              {trackerError}
            </div>
          )}
        </div>

        {/* Modal Action Footer */}
        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/60 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          {/* Secondary Actions (Save & Dismiss) */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onToggleSave(match.id)}
              className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border transition-colors cursor-pointer ${
                match.saved
                  ? 'bg-amber-50 text-amber-800 border-amber-300'
                  : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
              }`}
            >
              {match.saved ? <BookmarkCheck size={14} /> : <Bookmark size={14} />}
              <span>{match.saved ? 'Saved' : 'Save'}</span>
            </button>

            <button
              type="button"
              onClick={() => {
                onDismiss(match.id);
                onClose();
              }}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-600 bg-white border border-slate-200 hover:bg-slate-50 hover:text-slate-800 transition-colors cursor-pointer"
            >
              <EyeOff size={14} />
              <span>Dismiss</span>
            </button>

            {job.application_url && (
              <a
                href={job.application_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-600 bg-white border border-slate-200 hover:bg-slate-50 transition-colors"
              >
                <span>External Link</span>
                <ExternalLink size={13} />
              </a>
            )}
          </div>

          {/* Primary Action Buttons */}
          <div className="flex items-center gap-2 flex-wrap">
            <button
              type="button"
              onClick={handleAnalyzeResume}
              className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-white border border-[#CBD5E1] text-[#1B2A4A] text-xs font-semibold hover:bg-slate-100 transition-colors cursor-pointer"
            >
              <FileSearch size={14} />
              <span>Tailor Resume</span>
            </button>

            {!job.application_url && (
              <button
                type="button"
                disabled={isAddingToTracker || addedSuccess}
                onClick={handleAddToTracker}
                className={`inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                  addedSuccess
                    ? 'bg-emerald-600 text-white cursor-default'
                    : 'bg-white border border-[#CBD5E1] text-[#1B2A4A] hover:bg-slate-50'
                }`}
              >
                {addedSuccess ? (
                  <>
                    <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                      <CheckCircle2 size={14} aria-hidden="true" focusable="false" />
                    </span>
                    <span>Added to Tracker</span>
                  </>
                ) : (
                  <>
                    <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                      <PlusCircle size={14} aria-hidden="true" focusable="false" />
                    </span>
                    <span>{isAddingToTracker ? 'Adding...' : 'Add to Track Jobs'}</span>
                  </>
                )}
              </button>
            )}

            {job.application_url && (
              <button
                type="button"
                disabled={isApplying}
                onClick={handleApply}
                className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-[#1B2A4A] hover:bg-[#142038] text-white text-xs font-bold transition-all shadow-xs cursor-pointer active:scale-95 disabled:opacity-50"
              >
                <ExternalLink size={14} />
                <span>{isApplying ? 'Opening...' : 'Apply'}</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

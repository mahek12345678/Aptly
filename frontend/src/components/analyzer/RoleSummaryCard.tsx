import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, MapPin, Calendar, DollarSign, Briefcase, Plus, Check, ExternalLink, Award } from 'lucide-react';
import { JobDetails } from '@/types/jd-analyzer';
import { api } from '@/lib/api';
import { startApplicationIntent } from '@/lib/applyIntent';

interface RoleSummaryCardProps {
  job: JobDetails;
  rawJd: string;
  applicationUrl?: string | null;
  sourceJobId?: string | null;
}

export function RoleSummaryCard({ job, rawJd, applicationUrl, sourceJobId }: RoleSummaryCardProps) {
  const navigate = useNavigate();
  const [isAdding, setIsAdding] = useState(false);
  const [isAdded, setIsAdded] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const targetUrl = job.application_url || applicationUrl || null;

  const handleApply = async () => {
    if (!targetUrl) return;
    setIsApplying(true);
    setActionError(null);
    try {
      await startApplicationIntent({
        company: job.company,
        role: job.role_title,
        location: job.location || null,
        deadline: job.deadline ? new Date(job.deadline).toISOString() : null,
        compensation: job.compensation || null,
        job_description: rawJd,
        application_url: targetUrl,
        source: 'JD Analyzer',
        source_job_id: sourceJobId || null,
      });
      setIsAdded(true);
    } catch (err: any) {
      setActionError(err?.message || 'Failed to start application.');
    } finally {
      setIsApplying(false);
    }
  };

  const handleAddToTracker = async () => {
    setIsAdding(true);
    setActionError(null);
    try {
      await api.post('/api/v1/applications', {
        company: job.company,
        role: job.role_title,
        location: job.location || null,
        deadline: job.deadline ? new Date(job.deadline).toISOString() : null,
        stipend: job.compensation || null,
        job_description: rawJd,
        status: 'applied',
        source: 'JD Analyzer',
        source_job_id: sourceJobId || null,
      });
      setIsAdded(true);
    } catch (err: any) {
      setActionError(err?.message || 'Failed to add application.');
    } finally {
      setIsAdding(false);
    }
  };

  return (
    <div className="p-5 sm:p-6 rounded-xl bg-white border border-[#E2E2E2] shadow-2xs">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        {/* Left: Role & Company Info */}
        <div className="space-y-2 max-w-2xl">
          <div className="flex items-center gap-2">
            <span
              className="p-1.5 rounded-lg bg-[#F1F5F9] text-[#1B2A4A] border border-[#E2E8F0]"
              aria-hidden="true"
            >
              <Building2 size={16} aria-hidden="true" focusable="false" />
            </span>
            <span className="text-xs font-semibold uppercase tracking-wider text-[#6B6B6B]">
              {job.company}
            </span>
            {job.internal_grade && (
              <span
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-[#F1F5F9] border border-[#CBD5E1] text-[#475569]"
                aria-label={`Internal Grade ${job.internal_grade}`}
              >
                <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                  <Award size={11} className="text-[#64748B]" aria-hidden="true" focusable="false" />
                </span>
                <span>Grade {job.internal_grade}</span>
              </span>
            )}
          </div>

          <h2 className="font-serif text-xl sm:text-2xl font-bold text-[#1A1A1A] tracking-tight">
            {job.role_title}
          </h2>

          {job.role_summary && (
            <p className="text-xs text-[#4B5563] leading-relaxed pt-0.5">
              {job.role_summary}
            </p>
          )}

          {/* Badges */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            {job.location && (
              <span
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#F8FAFC] border border-[#E2E8F0] text-xs text-[#4B5563]"
                aria-label={job.location}
              >
                <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                  <MapPin size={12} className="text-[#94A3B8]" aria-hidden="true" focusable="false" />
                </span>
                <span>{job.location}</span>
              </span>
            )}

            {job.employment_type && (
              <span
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#F8FAFC] border border-[#E2E8F0] text-xs text-[#4B5563]"
                aria-label={job.employment_type}
              >
                <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                  <Briefcase size={12} className="text-[#94A3B8]" aria-hidden="true" focusable="false" />
                </span>
                <span>{job.employment_type}</span>
              </span>
            )}

            {job.compensation && (
              <span
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#F8FAFC] border border-[#E2E8F0] text-xs text-[#4B5563]"
                aria-label={job.compensation}
              >
                <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                  <DollarSign size={12} className="text-[#94A3B8]" aria-hidden="true" focusable="false" />
                </span>
                <span>{job.compensation}</span>
              </span>
            )}

            {job.deadline && (
              <span
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#F8FAFC] border border-[#E2E8F0] text-xs text-[#4B5563]"
                aria-label={`Deadline: ${job.deadline}`}
              >
                <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                  <Calendar size={12} className="text-[#94A3B8]" aria-hidden="true" focusable="false" />
                </span>
                <span>Deadline: {job.deadline}</span>
              </span>
            )}
          </div>
        </div>

        {/* Right: Apply or Add to Track Jobs Button */}
        <div className="shrink-0 flex flex-col items-start sm:items-end gap-1.5">
          {isAdded ? (
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#E8F5EE] border border-[#A7F3D0] text-xs font-semibold text-[#1E4D3A]">
                <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                  <Check size={14} aria-hidden="true" focusable="false" />
                </span>
                <span>{targetUrl ? 'Application Started' : 'Added to Track Jobs'}</span>
              </span>
              <button
                type="button"
                onClick={() => navigate('/track-jobs')}
                aria-label="View Board"
                className="text-xs text-[#3D5580] hover:underline font-semibold cursor-pointer"
              >
                View Board →
              </button>
            </div>
          ) : targetUrl ? (
            <button
              type="button"
              onClick={handleApply}
              disabled={isApplying}
              aria-label="Apply to this role"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#1B2A4A] hover:bg-[#142038] text-white text-xs font-semibold transition-all shadow-xs disabled:opacity-50 cursor-pointer active:scale-95"
            >
              <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                <ExternalLink size={14} aria-hidden="true" focusable="false" />
              </span>
              <span>{isApplying ? 'Opening...' : 'Apply to this role'}</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={handleAddToTracker}
              disabled={isAdding}
              aria-label="Add to Track Jobs"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#1B2A4A] hover:bg-[#142038] text-white text-xs font-semibold transition-colors shadow-xs disabled:opacity-50 cursor-pointer"
            >
              <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                <Plus size={15} aria-hidden="true" focusable="false" />
              </span>
              <span>{isAdding ? 'Adding...' : 'Add to Track Jobs'}</span>
            </button>
          )}

          {actionError && (
            <span className="text-[11px] text-[#991B1B]">{actionError}</span>
          )}
        </div>
      </div>
    </div>
  );
}

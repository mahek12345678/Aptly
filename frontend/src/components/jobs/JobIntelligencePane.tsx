import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bookmark, ArrowRight, ExternalLink } from 'lucide-react';
import { JobMatchItem } from '@/types/jobs';
import { startApplicationIntent } from '@/lib/applyIntent';
import { MatchMapVisual } from './MatchMapVisual';
import { extractJobIntelligence } from '@/lib/jobPresentation';

interface JobIntelligencePaneProps {
  match: JobMatchItem | null;
  rank: number;
  onToggleSave: (matchId: string) => Promise<void>;
}

export const JobIntelligencePane: React.FC<JobIntelligencePaneProps> = ({
  match,
  rank,
  onToggleSave,
}) => {
  const navigate = useNavigate();
  const [isApplying, setIsApplying] = useState(false);
  const [fadeState, setFadeState] = useState(true);

  // Trigger gentle 150ms crossfade on match change
  useEffect(() => {
    setFadeState(false);
    const timer = setTimeout(() => setFadeState(true), 40);
    return () => clearTimeout(timer);
  }, [match?.id]);

  if (!match) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 text-center text-[#6B6B6B] bg-white">
        <p className="text-sm">Select an opportunity to view grounded role intelligence.</p>
      </div>
    );
  }

  const { job } = match;

  // Extract intelligence (matched skills, gaps, grounded evidence, structured JD)
  const intelligence = extractJobIntelligence(
    job.description,
    match.match_reasons,
    job.role_title,
    job.company,
    job.location,
    job.employment_type
  );

  // Format posted time
  const formatPostedTime = (isoString?: string | null) => {
    if (!isoString) return null;
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return null;
    const diffHours = Math.floor((Date.now() - date.getTime()) / 3600000);
    if (diffHours < 1) return 'Posted just now';
    if (diffHours < 24) return `Posted ${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return 'Posted yesterday';
    return `Posted ${diffDays}d ago`;
  };

  const postedText = formatPostedTime(job.posted_at);

  // Subtitle parts
  const subMetaParts: string[] = [];
  if (job.location) subMetaParts.push(job.location);
  if (job.employment_type) {
    subMetaParts.push(job.employment_type.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase()));
  }
  if (job.compensation && job.compensation.trim()) {
    subMetaParts.push(job.compensation.trim());
  }

  // Handle Apply Action
  const handleApply = async () => {
    setIsApplying(true);
    try {
      await startApplicationIntent({
        company: job.company,
        role: job.role_title,
        location: job.location || 'Remote',
        deadline: job.deadline,
        compensation: job.compensation,
        job_description: job.description,
        application_url: job.application_url,
        source: job.source || 'Job Matching',
        source_job_id: job.id,
      });
    } catch (err) {
      console.error('Apply intent error:', err);
    } finally {
      setIsApplying(false);
    }
  };

  // Handle Analyze & Tailor Navigation
  const handleAnalyzeAndTailor = () => {
    navigate('/jd-analyzer', {
      state: {
        description: job.description,
        jobDescription: job.description,
        company: job.company,
        role_title: job.role_title,
        roleTitle: job.role_title,
        source_job_id: job.id,
        sourceJobId: job.id,
        application_url: job.application_url,
        applicationUrl: job.application_url,
      },
    });
  };

  // Company initial letter
  const initial = job.company ? job.company.charAt(0).toUpperCase() : 'A';

  const formattedSource = job.source
    ? job.source.toLowerCase() === 'adzuna'
      ? 'Adzuna'
      : job.source.toLowerCase() === 'remotive'
      ? 'Remotive'
      : job.source.replace(/\b\w/g, (c) => c.toUpperCase())
    : 'Adzuna';

  return (
    <div
      className={`flex-1 h-full overflow-y-auto bg-white transition-opacity duration-150 ${
        fadeState ? 'opacity-100' : 'opacity-0'
      }`}
    >
      {/* Sticky / Fixed Header */}
      <div className="p-6 border-b border-[#E2E2E2] bg-white sticky top-0 z-10 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          {/* Left: Avatar + Title + Meta */}
          <div className="flex items-start gap-3.5 min-w-0">
            <div className="w-11 h-11 rounded-lg bg-[#4F46E5] text-white flex items-center justify-center font-bold text-lg font-serif shrink-0 shadow-2xs">
              {initial}
            </div>

            <div className="min-w-0">
              <p className="text-xs text-[#6B6B6B] font-medium tracking-wide">
                {job.company}
                <span className="text-[#9CA3AF]"> · Source: {formattedSource}</span>
              </p>
              <h1 className="font-serif text-2xl font-bold text-[#1A1A1A] tracking-tight mt-0.5 leading-snug">
                {job.role_title}
              </h1>
              {subMetaParts.length > 0 && (
                <p className="text-xs text-[#6B6B6B] mt-1 truncate">
                  {subMetaParts.join(' · ')}
                </p>
              )}
              {postedText && (
                <p className="text-[11px] text-[#9CA3AF] mt-0.5">
                  {postedText}
                </p>
              )}
            </div>
          </div>

          {/* Right: Score Card */}
          <div className="shrink-0 flex flex-col items-center sm:items-end">
            <div className="bg-[#EAF5F0] border border-[#CDE7DC] rounded-xl px-4 py-2 text-center min-w-[105px]">
              <span className="font-mono text-2xl font-bold text-[#1E7E51] leading-none block">
                {Math.round(match.final_score)}%
              </span>
              <span className="text-[10px] font-semibold text-[#1E7E51] uppercase tracking-wider block mt-1">
                ✓ Profile Match
              </span>
            </div>
            <span className="text-[10.5px] text-[#6B6B6B] mt-1 font-mono">
              Ranked #{rank} Candidate Pool
            </span>
          </div>
        </div>

        {/* Action Buttons Row */}
        <div className="flex items-center gap-2.5 mt-5">
          {/* Save Button */}
          <button
            type="button"
            onClick={() => onToggleSave(match.id)}
            className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border text-xs font-medium transition-colors cursor-pointer ${
              match.saved
                ? 'bg-[#1B2A4A] text-white border-[#1B2A4A]'
                : 'bg-white text-[#1A1A1A] border-[#E2E2E2] hover:bg-slate-50'
            }`}
          >
            <Bookmark
              size={13}
              className={match.saved ? 'fill-current text-white' : 'text-[#6B6B6B]'}
              aria-hidden="true"
              focusable="false"
            />
            <span>{match.saved ? 'Saved' : 'Save'}</span>
          </button>

          {/* Analyze & Tailor Button */}
          <button
            type="button"
            onClick={handleAnalyzeAndTailor}
            aria-label="Analyze and Tailor"
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-[#E2E2E2] bg-white text-[#1A1A1A] text-xs font-medium hover:bg-slate-50 transition-colors cursor-pointer"
          >
            <span>Analyze & Tailor</span>
          </button>

          {/* Apply Button (Strongest CTA) */}
          <button
            type="button"
            onClick={handleApply}
            disabled={isApplying}
            aria-label="Apply to job"
            className="inline-flex items-center gap-1.5 px-5 py-1.5 rounded-lg bg-[#1B2A4A] hover:bg-[#142038] text-white text-xs font-semibold transition-colors cursor-pointer shadow-2xs ml-auto disabled:opacity-60"
          >
            <span>{isApplying ? 'Opening...' : 'Apply'}</span>
            <ArrowRight size={13} aria-hidden="true" focusable="false" />
          </button>
        </div>
      </div>

      {/* Detail Content Body */}
      <div className="p-6 space-y-7">
        {/* 1. MATCH BREAKDOWN */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-[11px] font-bold uppercase tracking-wider text-[#1A1A1A]">
              MATCH BREAKDOWN
            </h2>
          </div>

          {(() => {
            const simScore = match.similarity_score <= 1.0 && match.final_score > 1.0 ? Math.round(match.similarity_score * 100) : Math.round(match.similarity_score);
            const prefScore = match.preference_score <= 1.0 && match.final_score > 1.0 ? Math.round(match.preference_score * 100) : Math.round(match.preference_score);
            const finalScore = match.final_score <= 1.0 ? Math.round(match.final_score * 100) : Math.round(match.final_score);
            return (
              <div className="p-4 rounded-xl border border-[#E2E2E2] bg-[#FAFAFA] space-y-3">
                {/* Resume Similarity Rail */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[#6B6B6B]">Resume Similarity</span>
                    <span className="font-mono font-semibold text-[#1A1A1A]">
                      {simScore}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-slate-200/70 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#1B2A4A] rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(100, simScore)}%` }}
                    />
                  </div>
                </div>

                {/* Preference Fit Rail */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[#6B6B6B]">Preference Fit</span>
                    <span className="font-mono font-semibold text-[#1A1A1A]">
                      {prefScore}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-slate-200/70 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#3D5580] rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(100, prefScore)}%` }}
                    />
                  </div>
                </div>

                <div className="border-t border-[#E2E2E2] pt-2" />

                {/* Final Match Rail */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-[#1A1A1A]">Final Match</span>
                    <span className="font-mono font-bold text-[#1E7E51]">
                      {finalScore}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-slate-200/70 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#1E7E51] rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(100, finalScore)}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })()}
        </div>

        {/* 2. SIGNATURE VISUAL: RESUME ↔ ROLE MATCH MAP */}
        <MatchMapVisual
          matchedSkills={intelligence.matchedSkills}
          missingSkills={intelligence.gapSkills}
          roleSkills={intelligence.matchedSkills}
        />

        {/* 3. WHY THIS MATCHES */}
        <div className="space-y-2.5">
          <h2 className="font-serif text-lg font-bold text-[#1A1A1A]">
            Why This Matches
          </h2>

          <div className="space-y-2 text-xs sm:text-[13px] text-[#4A5568] leading-relaxed">
            {intelligence.evidenceStatements.map((stmt, idx) => (
              <p key={idx} className="flex items-start gap-2">
                <span className="text-[#1E7E51] font-bold shrink-0">✓</span>
                <span>{stmt.replace(/^✓\s*/, '')}</span>
              </p>
            ))}
          </div>
        </div>

        {/* 4. MATCHED COMPETENCIES & POTENTIAL GAPS */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 pt-1">
          {/* Matched Competencies */}
          <div className="space-y-2">
            <h3 className="text-[11px] font-mono uppercase tracking-wider text-[#6B6B6B]">
              MATCHED COMPETENCIES
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {intelligence.matchedSkills.map((skill, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[#EAF5F0] text-[#1E7E51] text-xs font-medium border border-[#CDE7DC]"
                >
                  <span>✓</span>
                  <span>{skill}</span>
                </span>
              ))}
            </div>
          </div>

          {/* Potential Gaps */}
          <div className="space-y-2">
            <h3 className="text-[11px] font-mono uppercase tracking-wider text-[#6B6B6B]">
              POTENTIAL GAPS
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {intelligence.gapSkills.length > 0 ? (
                intelligence.gapSkills.map((gap, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[#F1F3F5] text-[#4A5568] text-xs font-medium border border-[#E2E2E2]"
                  >
                    <span>+</span>
                    <span>{gap}</span>
                  </span>
                ))
              ) : (
                <span className="text-xs text-[#9CA3AF] italic">
                  No critical requirement gaps detected
                </span>
              )}
            </div>
          </div>
        </div>

        {/* 5. ROLE OVERVIEW & OPERATIONAL SCOPE */}
        <div className="space-y-4 pt-2 border-t border-[#E2E2E2]">
          <h2 className="font-serif text-lg font-bold text-[#1A1A1A]">
            Role Overview & Operational Scope
          </h2>

          <div className="text-xs sm:text-[13px] text-[#4A5568] leading-relaxed">
            <p>{intelligence.overview}</p>
          </div>

          {/* Responsibilities */}
          {intelligence.responsibilities.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-[11px] font-mono uppercase tracking-wider text-[#1A1A1A] font-semibold">
                RESPONSIBILITIES
              </h3>
              <ul className="space-y-1.5 text-xs sm:text-[13px] text-[#4A5568]">
                {intelligence.responsibilities.map((resp, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-[#1B2A4A] mt-1 shrink-0">•</span>
                    <span>{resp}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Requirements */}
          {intelligence.requirements.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-[11px] font-mono uppercase tracking-wider text-[#1A1A1A] font-semibold">
                REQUIREMENTS
              </h3>
              <ul className="space-y-1.5 text-xs sm:text-[13px] text-[#4A5568]">
                {intelligence.requirements.map((req, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-[#1B2A4A] mt-1 shrink-0">•</span>
                    <span>{req}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Nice to Have */}
          {intelligence.niceToHave.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-[11px] font-mono uppercase tracking-wider text-[#1A1A1A] font-semibold">
                NICE TO HAVE
              </h3>
              <ul className="space-y-1.5 text-xs sm:text-[13px] text-[#4A5568]">
                {intelligence.niceToHave.map((nth, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-[#6B6B6B] mt-1 shrink-0">•</span>
                    <span>{nth}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Application Details */}
          <div className="p-4 rounded-xl border border-[#E2E2E2] bg-[#FAFAFA] space-y-1.5 text-xs text-[#6B6B6B]">
            <h3 className="text-[11px] font-mono uppercase tracking-wider text-[#1A1A1A] font-semibold pb-1">
              APPLICATION DETAILS
            </h3>
            {job.posted_at && (
              <p>
                <span className="font-semibold text-[#1A1A1A]">Posted:</span> {new Date(job.posted_at).toLocaleDateString()}
              </p>
            )}
            {job.employment_type && (
              <p>
                <span className="font-semibold text-[#1A1A1A]">Employment:</span>{' '}
                {job.employment_type.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
              </p>
            )}
            {job.location && (
              <p>
                <span className="font-semibold text-[#1A1A1A]">Location:</span> {job.location}
              </p>
            )}
            {job.source && (
              <p>
                <span className="font-semibold text-[#1A1A1A]">Source:</span> {formattedSource}
              </p>
            )}
            {job.application_url && (
              <p className="pt-1">
                <a
                  href={job.application_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#1B2A4A] font-medium hover:underline inline-flex items-center gap-1"
                >
                  <span>Direct Provider Link</span>
                  <ExternalLink size={11} />
                </a>
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

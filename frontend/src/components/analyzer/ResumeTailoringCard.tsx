import { useState } from 'react';
import { Copy, Check, ShieldCheck, ChevronRight, Bookmark, Info } from 'lucide-react';
import { TailoredSections, TailorResumeResponse } from '@/types/jd-analyzer';
import { api } from '@/lib/api';

interface ResumeTailoringCardProps {
  resumeId: string;
  rawJd: string;
  sourceJobId?: string | null;
  company?: string | null;
  roleTitle?: string | null;
}

export function ResumeTailoringCard({ resumeId, rawJd, sourceJobId, company, roleTitle }: ResumeTailoringCardProps) {
  const [tailored, setTailored] = useState<TailoredSections | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [summaryAccepted, setSummaryAccepted] = useState<boolean | null>(null);

  const handleGenerateTailoring = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const res = await api.post<TailorResumeResponse>('/api/v1/jd/tailor', {
        job_description: rawJd,
        resume_id: resumeId,
        source_job_id: sourceJobId || null,
        company: company || null,
        role_title: roleTitle || null,
      });
      setTailored(res.tailored_sections);
    } catch (err: any) {
      setError(err?.message || 'Failed to generate tailored suggestions.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="p-5 sm:p-6 rounded-xl bg-white border border-[#E2E2E2] shadow-2xs space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#E2E2E2]">
        <div>
          <div
            className="flex items-center gap-1.5 text-xs font-semibold text-[#1B2A4A] uppercase tracking-wider"
            aria-label="Resume Tailoring"
          >
            <span>Resume Tailoring</span>
          </div>
          <p className="text-xs text-[#6B6B6B] mt-0.5">
            Targeted adjustments emphasizing relevant content without fabricating credentials.
          </p>
        </div>

        {!tailored && (
          <button
            type="button"
            onClick={handleGenerateTailoring}
            disabled={isGenerating}
            aria-label="Generate tailored suggestions"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#3D5580] hover:bg-[#2B3C5A] text-white text-xs font-semibold transition-colors shadow-xs disabled:opacity-50 cursor-pointer"
          >
            <span>{isGenerating ? 'Generating Suggestions...' : 'Generate Tailored Version'}</span>
          </button>
        )}
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-[#FEF2F2] border border-[#FCA5A5] text-[#991B1B] text-xs flex items-center justify-between">
          <span>{error}</span>
          <button
            type="button"
            onClick={handleGenerateTailoring}
            className="font-semibold underline ml-2 cursor-pointer hover:text-[#7F1D1D]"
          >
            Retry Tailoring
          </button>
        </div>
      )}

      {/* Before generation preview */}
      {!tailored && !isGenerating && (
        <div className="p-6 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] text-center space-y-3">
          <div className="w-10 h-10 rounded-full bg-white border border-[#CBD5E1] text-[#3D5580] flex items-center justify-center mx-auto">
            <span aria-hidden="true" className="inline-flex shrink-0 select-none">
              <ShieldCheck size={20} aria-hidden="true" focusable="false" />
            </span>
          </div>
          <div className="max-w-md mx-auto">
            <h4 className="text-xs font-bold text-[#1A1A1A]">Anti-Hallucination Resume Strategy</h4>
            <p className="text-xs text-[#6B6B6B] mt-1 leading-relaxed">
              Aptly reorders verified bullet points, prioritizes matched technical keywords, and crafts a conservative transferable summary based strictly on verified resume facts.
            </p>
          </div>
          <button
            type="button"
            onClick={handleGenerateTailoring}
            aria-label="Generate Tailored Version"
            className="text-xs text-[#1B2A4A] font-semibold hover:underline cursor-pointer"
          >
            Click "Generate Tailored Version" above to view custom sections →
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {isGenerating && (
        <div className="space-y-4 animate-pulse">
          <div className="h-20 bg-[#F1F5F9] rounded-lg border border-[#E2E8F0]" />
          <div className="h-16 bg-[#F1F5F9] rounded-lg border border-[#E2E8F0]" />
          <div className="h-24 bg-[#F1F5F9] rounded-lg border border-[#E2E8F0]" />
        </div>
      )}

      {/* Tailored Sections Display */}
      {tailored && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {(tailored.summary?.strategy?.includes('Tailoring is limited') ||
            tailored.skills?.strategy?.includes('Tailoring is limited')) && (
            <div className="p-4 rounded-xl bg-[#FFFBEB] border border-[#FDE68A] text-[#92400E] space-y-2.5 animate-in fade-in duration-150">
              <div className="flex items-center gap-2 font-bold text-xs">
                <Info size={16} className="text-[#B45309] shrink-0" aria-hidden="true" focusable="false" />
                <span>Tailoring is limited because the complete job requirements are unavailable.</span>
              </div>
              <p className="text-xs text-[#B45309] leading-relaxed">
                General verified resume strengths are highlighted below without claiming alignment to unverified role requirements.
              </p>
              <div className="pt-1">
                <button
                  type="button"
                  onClick={() => {
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                    const ta = document.querySelector('textarea');
                    if (ta) {
                      ta.focus();
                      ta.select();
                    }
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#B45309] hover:bg-[#92400E] text-white text-xs font-semibold shrink-0 transition-colors shadow-xs cursor-pointer"
                >
                  <span>Paste full JD to unlock precise tailoring</span>
                </button>
              </div>
            </div>
          )}

          {/* 1. Summary with [Accept] [Keep original] [Copy] */}
          {tailored.summary && (
            <div className="p-4 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <span className="text-xs font-bold text-[#1A1A1A] uppercase tracking-wider">
                  Targeted Summary
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setSummaryAccepted(true)}
                    aria-label="Accept suggestion"
                    className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium transition-colors cursor-pointer ${
                      summaryAccepted === true
                        ? 'bg-[#E8F5EE] text-[#1E4D3A] border border-[#A7F3D0]'
                        : 'bg-white text-[#334155] border border-[#CBD5E1] hover:bg-[#F1F5F9]'
                    }`}
                  >
                    <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                      <Check size={12} aria-hidden="true" focusable="false" />
                    </span>
                    <span>{summaryAccepted === true ? 'Accepted' : 'Accept'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setSummaryAccepted(false)}
                    aria-label="Keep original"
                    className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium transition-colors cursor-pointer ${
                      summaryAccepted === false
                        ? 'bg-[#EFF6FF] text-[#1E40AF] border border-[#BFDBFE]'
                        : 'bg-white text-[#64748B] border border-[#CBD5E1] hover:bg-[#F1F5F9]'
                    }`}
                  >
                    <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                      <Bookmark size={12} aria-hidden="true" focusable="false" />
                    </span>
                    <span>Keep original</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleCopy(tailored.summary.suggestion, 'summary')}
                    aria-label="Copy summary"
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-white border border-[#CBD5E1] text-[11px] text-[#3D5580] hover:text-[#1B2A4A] font-medium transition-colors cursor-pointer"
                  >
                    {copiedKey === 'summary' ? (
                      <>
                        <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                          <Check size={12} className="text-[#16A34A]" aria-hidden="true" focusable="false" />
                        </span>
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                          <Copy size={12} aria-hidden="true" focusable="false" />
                        </span>
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              <p className="text-xs text-[#334155] leading-relaxed italic bg-white p-3 rounded border border-[#E2E8F0]">
                "{tailored.summary.suggestion}"
              </p>
              {tailored.summary.strategy && (
                <p className="text-[11px] text-[#64748B]">Strategy: {tailored.summary.strategy}</p>
              )}
            </div>
          )}

          {/* 2. Skills Section Ordering: PRIORITIZE, KEEP SECONDARY, TARGET / LEARN */}
          {tailored.skills && (
            <div className="p-4 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] space-y-4">
              <div>
                <span className="text-xs font-bold text-[#1A1A1A] uppercase tracking-wider block">
                  Skills Section Ordering
                </span>
                <p className="text-[11px] text-[#64748B] mt-0.5">
                  Organize your skills section with verified job matches first. Never claim unverified gaps as existing skills.
                </p>
              </div>

              {/* Group 1: PRIORITIZE */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold text-[#1E4D3A] uppercase tracking-wider block">
                  PRIORITIZE (Verified & Critical to Role)
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {tailored.skills.prioritized.map((sk) => (
                    <span
                      key={sk}
                      className="px-2.5 py-1 rounded bg-[#E8F5EE] border border-[#A7F3D0] text-xs font-semibold text-[#1E4D3A]"
                    >
                      {sk}
                    </span>
                  ))}
                  {tailored.skills.prioritized.length === 0 && (
                    <span className="text-xs text-[#6B6B6B] italic">No direct matches identified.</span>
                  )}
                </div>
              </div>

              {/* Group 2: KEEP SECONDARY */}
              <div className="space-y-1.5 pt-1">
                <span className="text-[10px] font-bold text-[#475569] uppercase tracking-wider block">
                  KEEP SECONDARY (Verified Transferable Skills)
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {tailored.skills.secondary.map((sk) => (
                    <span
                      key={sk}
                      className="px-2.5 py-1 rounded bg-white border border-[#E2E8F0] text-xs text-[#475569]"
                    >
                      {sk}
                    </span>
                  ))}
                  {tailored.skills.secondary.length === 0 && (
                    <span className="text-xs text-[#6B6B6B] italic">None.</span>
                  )}
                </div>
              </div>

              {/* Group 3: TARGET / LEARN */}
              {tailored.skills.target_gaps && tailored.skills.target_gaps.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <span className="text-[10px] font-bold text-[#92400E] uppercase tracking-wider block">
                    TARGET / LEARN (Genuine Role Gaps — Study Focus)
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {tailored.skills.target_gaps.map((sk) => {
                      const hasSource = sk.includes('(Source:');
                      if (hasSource) {
                        const parts = sk.split('(Source:');
                        const skillName = parts[0].trim();
                        const sourceName = parts[1].replace(')', '').trim();
                        return (
                          <div
                            key={sk}
                            className="inline-flex flex-col px-2.5 py-1 rounded bg-[#FFFBEB] border border-[#FDE68A] text-xs text-[#92400E]"
                          >
                            <span className="font-medium">△ {skillName}</span>
                            <span className="text-[10px] text-[#B45309] font-normal">
                              Source: {sourceName}
                            </span>
                          </div>
                        );
                      }
                      return (
                        <span
                          key={sk}
                          className="px-2.5 py-1 rounded bg-[#FFFBEB] border border-[#FDE68A] text-xs text-[#92400E]"
                        >
                          △ {sk}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 3. Project Alignment (Supports vs Does Not Establish) */}
          {tailored.projects && tailored.projects.length > 0 && (
            <div className="p-4 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] space-y-3">
              <span className="text-xs font-bold text-[#1A1A1A] uppercase tracking-wider block">
                Portfolio Project Alignment
              </span>

              <div className="space-y-3">
                {tailored.projects.map((proj, idx) => (
                  <div key={idx} className="p-3.5 rounded bg-white border border-[#E2E8F0] space-y-2 text-xs">
                    <span className="text-[#1E293B] font-bold text-sm leading-relaxed block">
                      {proj.project_title || proj.original_entry}
                    </span>

                    {/* Aggregated Project Bullets */}
                    {proj.project_bullets && proj.project_bullets.length > 0 && (
                      <ul className="list-disc list-inside space-y-1 text-[11px] text-[#475569] bg-[#F8FAFC] p-2.5 rounded border border-[#F1F5F9]">
                        {proj.project_bullets.map((b, bIdx) => (
                          <li key={bIdx} className="leading-relaxed">
                            {b}
                          </li>
                        ))}
                      </ul>
                    )}

                    {/* What it supports */}
                    {proj.supports && proj.supports.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-0.5">
                        <span className="text-[10px] font-bold text-[#1E4D3A] uppercase tracking-wider w-full block">
                          Demonstrates:
                        </span>
                        {proj.supports.map((sup, sIdx) => (
                          <span
                            key={sIdx}
                            className="px-2 py-0.5 rounded bg-[#E8F5EE] text-[#1E4D3A] text-[11px] font-medium"
                          >
                            {sup}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Related Evidence */}
                    {proj.related_evidence && proj.related_evidence.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-0.5">
                        <span className="text-[10px] font-bold text-[#1E40AF] uppercase tracking-wider w-full block">
                          Related Evidence:
                        </span>
                        {proj.related_evidence.map((rel, rIdx) => (
                          <span
                            key={rIdx}
                            className="px-2 py-0.5 rounded bg-[#EFF6FF] border border-[#BFDBFE] text-[#1E40AF] text-[11px] font-medium"
                          >
                            {rel}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* What it does NOT establish */}
                    {proj.does_not_establish && proj.does_not_establish.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-0.5">
                        <span className="text-[10px] font-bold text-[#94A3B8] uppercase tracking-wider w-full block">
                          Does Not Establish:
                        </span>
                        {proj.does_not_establish.map((ne, neIdx) => (
                          <span
                            key={neIdx}
                            className="px-2 py-0.5 rounded bg-[#F8FAFC] border border-[#E2E8F0] text-[#64748B] text-[11px]"
                          >
                            {ne}
                          </span>
                        ))}
                      </div>
                    )}

                    <div className="flex items-start gap-1.5 text-[11px] text-[#1E293B] font-medium pt-2 border-t border-[#F1F5F9]">
                      <span className="font-bold text-[#3D5580] shrink-0">Recommendation:</span>
                      <span className="text-[#334155] leading-relaxed">"{proj.action_suggestion}"</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 4. Experience Bullet Point Recommendations */}
          {tailored.experience && tailored.experience.length > 0 && (
            <div className="p-4 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] space-y-3">
              <span className="text-xs font-bold text-[#1A1A1A] uppercase tracking-wider block">
                Experience Recommendations
              </span>

              <div className="space-y-3">
                {tailored.experience.map((entry, idx) => (
                  <div key={idx} className="p-3 rounded bg-white border border-[#E2E8F0] space-y-1.5 text-xs">
                    <span className="text-[#334155] font-medium leading-relaxed block">
                      {entry.original_entry}
                    </span>

                    <div className="flex items-center gap-1.5 text-[11px] text-[#3D5580] font-medium pt-1 border-t border-[#F1F5F9]">
                      <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                        <ChevronRight size={12} aria-hidden="true" focusable="false" />
                      </span>
                      <span>{entry.action_suggestion}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

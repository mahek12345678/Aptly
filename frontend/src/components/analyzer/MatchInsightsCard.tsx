import { CheckCircle2, AlertCircle, ShieldAlert, Award, Layers } from 'lucide-react';
import { MatchAnalysis } from '@/types/jd-analyzer';

interface MatchInsightsCardProps {
  analysis: MatchAnalysis;
  resumeFilename: string;
}

export function MatchInsightsCard({ analysis, resumeFilename }: MatchInsightsCardProps) {
  const score = analysis.overall_match_score;
  const breakdown = analysis.match_breakdown;
  const seniority = analysis.seniority_alignment;
  const isInsufficient =
    analysis.insufficient_requirements === true ||
    analysis.analysis_quality === 'INSUFFICIENT_REQUIREMENTS';

  // Single Source of Truth counts (derived directly from NormalizedRequirement)
  const verifiedCount =
    analysis.verified_count ??
    analysis.verified_matches?.length ??
    analysis.matched_skills.length;

  const relatedCount =
    analysis.related_count ??
    analysis.related_experience?.length ??
    0;

  const gapCount =
    analysis.gap_count ??
    analysis.gaps_breakdown?.length ??
    analysis.missing_skills.length;

  const totalRequirements =
    (analysis.normalized_requirements?.length ?? 0) ||
    (verifiedCount + relatedCount + gapCount);

  // Dynamic non-contradictory copy — zero requirements is distinct from zero gaps
  const gapsMessage: string = (() => {
    if (analysis.gaps_summary_message) return analysis.gaps_summary_message;
    if (totalRequirements === 0 || isInsufficient) {
      return "We couldn't identify enough explicit requirements in this job description to evaluate skill fit reliably.";
    }
    if (gapCount === 0) return 'All evaluated requirements have verified or related evidence.';
    return `${gapCount} requirement${gapCount > 1 ? 's' : ''} could not be verified from your resume.`;
  })();

  const isScoreWithheld = isInsufficient || score === null;

  const isPartial = analysis.analysis_quality === 'PARTIAL' || analysis.description_quality === 'PARTIAL';

  // Determine restrained color tone based on score
  const scoreBadgeBg = isScoreWithheld
    ? 'bg-[#F8FAFC] text-[#64748B] border-[#CBD5E1]'
    : isPartial
    ? 'bg-[#FFFBEB] text-[#92400E] border-[#FDE68A]'
    : score >= 75
    ? 'bg-[#E8F5EE] text-[#1E4D3A] border-[#A7F3D0]'
    : score >= 50
    ? 'bg-[#EFF6FF] text-[#1E40AF] border-[#BFDBFE]'
    : 'bg-[#FFFBEB] text-[#92400E] border-[#FDE68A]';

  const scoreBadgeLabel = isScoreWithheld
    ? 'Limited Evidence'
    : isPartial
    ? 'Partial JD / Limited Evidence'
    : score >= 75
    ? 'Strong Match'
    : score >= 50
    ? 'Potential Match'
    : 'Low Evidence Match';

  return (
    <div className="p-5 sm:p-6 rounded-xl bg-white border border-[#E2E2E2] shadow-2xs space-y-6">
      {/* 1. Candidate Fit Analysis Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-[#E2E2E2]">
        <div>
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[#6B6B6B]">
            Candidate Fit
          </span>
          <div className="flex items-baseline gap-3 mt-1">
            <span className="font-serif text-3xl sm:text-4xl font-extrabold text-[#1A1A1A] tracking-tight">
              {isScoreWithheld ? '\u2014' : `${score}%`}
            </span>
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${scoreBadgeBg}`}
            >
              {scoreBadgeLabel}
            </span>
          </div>
        </div>

        <div className="text-left sm:text-right">
          <span className="text-[11px] text-[#6B6B6B] block">Evaluated against:</span>
          <span className="text-xs font-medium text-[#1B2A4A] truncate max-w-[200px] inline-block font-mono bg-[#F8FAFC] px-2 py-0.5 rounded border border-[#E2E8F0]">
            {resumeFilename}
          </span>
        </div>
      </div>

      {/* Insufficient JD Evidence Banner */}
      {isScoreWithheld && (
        <div className="p-4 rounded-lg bg-[#FFFBEB] border border-[#FDE68A] text-[#92400E] text-xs leading-relaxed">
          <p className="font-bold uppercase tracking-wider mb-1 text-[10px]">Limited Job Description</p>
          <p>This listing doesn't contain enough explicit requirements for a reliable skill-by-skill score. Paste the complete job description to get a full analysis.</p>
        </div>
      )}

      {/* 2. Match Breakdown (Deterministic Component Scores) */}
      {breakdown && (
        <div className="space-y-2.5">
          <div
            className="text-[11px] font-bold uppercase tracking-wider text-[#6B6B6B] flex items-center gap-1.5"
            aria-label="Match Breakdown"
          >
            <span aria-hidden="true" className="inline-flex shrink-0 select-none">
              <Layers size={13} className="text-[#3D5580]" aria-hidden="true" focusable="false" />
            </span>
            <span>Match Breakdown</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[10px] font-semibold text-[#64748B] block uppercase tracking-wider">
                Required Skills
              </span>
              {breakdown.required_skills_score === null ? (
                <>
                  <span className="font-mono text-sm font-semibold text-[#94A3B8] block mt-0.5">N/A</span>
                  <span className="text-[10px] text-[#94A3B8] block mt-0.5 italic">Not identified</span>
                </>
              ) : (
                <>
                  <span className="font-serif text-lg font-bold text-[#1E293B] block mt-0.5">
                    {breakdown.required_skills_score}%
                  </span>
                  {totalRequirements <= 1 && (
                    <span className="text-[10px] text-[#64748B] block mt-0.5">
                      ({verifiedCount} of {totalRequirements} evaluated)
                    </span>
                  )}
                </>
              )}
            </div>

            <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[10px] font-semibold text-[#64748B] block uppercase tracking-wider">
                Preferred Skills
              </span>
              {breakdown.preferred_skills_score === null ? (
                <>
                  <span className="font-mono text-sm font-semibold text-[#94A3B8] block mt-0.5">N/A</span>
                  <span className="text-[10px] text-[#94A3B8] block mt-0.5 italic">Not identified</span>
                </>
              ) : (
                <span className="font-serif text-lg font-bold text-[#1E293B] block mt-0.5">
                  {breakdown.preferred_skills_score}%
                </span>
              )}
            </div>

            <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[10px] font-semibold text-[#64748B] block uppercase tracking-wider">
                Experience
              </span>
              {breakdown.experience_score === null ? (
                <>
                  <span className="font-mono text-sm font-semibold text-[#94A3B8] block mt-0.5">N/A</span>
                  <span className="text-[10px] text-[#94A3B8] block mt-0.5 italic">Not specified</span>
                </>
              ) : (
                <span className="font-serif text-lg font-bold text-[#1E293B] block mt-0.5">
                  {breakdown.experience_score}%
                </span>
              )}
            </div>

            <div className="p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[10px] font-semibold text-[#64748B] block uppercase tracking-wider">
                Role Alignment
              </span>
              <span className="font-serif text-lg font-bold text-[#1E293B] block mt-0.5">
                {breakdown.domain_score}%
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 3. Verified Matches */}
      <div className="space-y-2 pt-1">
        <div
          className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#1E4D3A]"
          aria-label={`Verified Matches (${verifiedCount})`}
        >
          <span aria-hidden="true" className="inline-flex shrink-0 select-none">
            <CheckCircle2 size={14} className="text-[#1E4D3A]" aria-hidden="true" focusable="false" />
          </span>
          <span>Verified Matches ({verifiedCount})</span>
        </div>

        {verifiedCount > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {analysis.verified_matches && analysis.verified_matches.length > 0 ? (
              analysis.verified_matches.map((item, idx) => (
                <span
                  key={idx}
                  className="px-2.5 py-1 rounded-md bg-[#E8F5EE] border border-[#A7F3D0] text-[#1E4D3A] text-xs font-medium"
                  title={item.notes || (item.evidence && item.evidence.join('; '))}
                >
                  ✓ {item.canonical_requirement || item.requirement}
                </span>
              ))
            ) : (
              analysis.matched_skills.map((skill) => (
                <span
                  key={skill}
                  className="px-2.5 py-1 rounded-md bg-[#E8F5EE] border border-[#A7F3D0] text-[#1E4D3A] text-xs font-medium"
                >
                  ✓ {skill}
                </span>
              ))
            )}
          </div>
        ) : (
          <p className="text-xs text-[#6B6B6B] italic">No direct verified skill matches detected in resume text.</p>
        )}
      </div>

      {/* 4. Related / Transferable Evidence */}
      <div className="space-y-2">
        <div
          className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#3D5580]"
          aria-label={`Related / Transferable Evidence (${relatedCount})`}
        >
          <span aria-hidden="true" className="inline-flex shrink-0 select-none">
            <Award size={14} className="text-[#3D5580]" aria-hidden="true" focusable="false" />
          </span>
          <span>Related / Transferable Evidence ({relatedCount})</span>
        </div>

        {relatedCount > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {analysis.related_experience?.map((rel, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded-md bg-[#F1F5F9] border border-[#CBD5E1] text-[#334155] text-xs font-medium"
                title={rel.notes || (rel.evidence && rel.evidence.join('; '))}
              >
                ~ {rel.canonical_requirement || rel.requirement}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-xs text-[#6B6B6B] italic">No related or transferable evidence identified.</p>
        )}
      </div>

      {/* 5. Gaps, Traits, and Eligibility */}
      {(() => {
        const allGaps = analysis.gaps_breakdown || [];
        const technicalGaps = allGaps.filter(
          (g) => g.score_component !== 'soft_traits' && g.score_component !== 'eligibility' && g.category !== 'soft_skill' && g.category !== 'education'
        );
        const unverifiedTraits = allGaps.filter(
          (g) => g.score_component === 'soft_traits' || g.category === 'soft_skill'
        );
        const eligibilityItems = allGaps.filter(
          (g) => g.score_component === 'eligibility' || g.category === 'education'
        );

        return (
          <div className="space-y-4">
            {/* Technical Gaps */}
            <div className="space-y-2">
              <div
                className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#64748B]"
                aria-label={`Technical Gaps (${technicalGaps.length})`}
              >
                <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                  <AlertCircle size={14} className="text-[#64748B]" aria-hidden="true" focusable="false" />
                </span>
                <span>Technical Gaps ({technicalGaps.length})</span>
              </div>

              {technicalGaps.length > 0 ? (
                <div className="space-y-2">
                  <div className="flex flex-wrap gap-1.5">
                    {technicalGaps.map((gapItem, idx) => (
                      <span
                        key={idx}
                        className="px-2.5 py-1 rounded-md bg-[#FAFAFA] border border-[#E2E2E2] text-[#64748B] text-xs font-normal"
                        title={gapItem.advice}
                      >
                        △ {gapItem.canonical_requirement || gapItem.requirement}
                      </span>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-xs text-[#1E4D3A] font-medium">
                  {totalRequirements === 0 || isInsufficient
                    ? gapsMessage
                    : 'No critical technical skill gaps identified.'}
                </p>
              )}
            </div>

            {/* Unverified Traits */}
            {unverifiedTraits.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-[#F1F5F9]">
                <div
                  className="text-xs font-bold uppercase tracking-wider text-[#64748B]"
                  aria-label={`Unverified Traits (${unverifiedTraits.length})`}
                >
                  Unverified Traits ({unverifiedTraits.length})
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {unverifiedTraits.map((traitItem, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-md bg-[#F8FAFC] border border-[#E2E8F0] text-[#64748B] text-xs font-normal"
                      title={traitItem.advice || 'Not directly verifiable from resume prose.'}
                    >
                      △ {traitItem.canonical_requirement || traitItem.requirement}
                    </span>
                  ))}
                </div>
                <p className="text-[11px] text-[#94A3B8] italic">
                  Behavioural attributes are evaluated during interviews and do not penalize your technical skill match.
                </p>
              </div>
            )}

            {/* Eligibility to Review */}
            {eligibilityItems.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-[#F1F5F9]">
                <div
                  className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#D97706]"
                  aria-label="Eligibility to Review"
                >
                  <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                    <AlertCircle size={14} className="text-[#D97706]" aria-hidden="true" focusable="false" />
                  </span>
                  <span>Eligibility to Review</span>
                </div>
                <div className="space-y-1">
                  {eligibilityItems.map((item, idx) => (
                    <div key={idx} className="p-2.5 rounded-lg bg-[#FFFBEB] border border-[#FDE68A] text-xs text-[#92400E]">
                      <span className="font-semibold block">{item.canonical_requirement || item.requirement}</span>
                      <p className="text-[11px] mt-0.5">{item.advice}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })()}

      {/* 6. Seniority & Experience Check */}
      {seniority && (
        <div
          className={`p-3.5 rounded-lg border text-xs ${
            seniority.is_gap
              ? 'bg-[#FFFBEB] border-[#FDE68A] text-[#92400E]'
              : 'bg-[#F8FAFC] border-[#E2E8F0] text-[#334155]'
          }`}
          aria-label="Seniority & Experience Check"
        >
          <div className="flex items-start gap-2.5">
            <span aria-hidden="true" className="inline-flex shrink-0 select-none mt-0.5">
              <ShieldAlert
                size={16}
                className={seniority.is_gap ? 'text-[#B45309]' : 'text-[#3D5580]'}
                aria-hidden="true"
                focusable="false"
              />
            </span>
            <div className="space-y-1 w-full">
              <span
                className={`font-bold block uppercase tracking-wider text-[10px] ${
                  seniority.is_gap ? 'text-[#B45309]' : 'text-[#3D5580]'
                }`}
              >
                Seniority &amp; Experience Check
              </span>
              <span className="font-semibold block">{seniority.status}</span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1 text-[11px]">
                <div>
                  <span className="text-[#64748B] block">Requested:</span>
                  <span className="font-medium text-[#1E293B]">{seniority.seniority_requested}</span>
                </div>
                <div>
                  <span className="text-[#64748B] block">Professional Experience:</span>
                  <span className="font-medium text-[#1E293B]">{seniority.candidate_seniority}</span>
                </div>
                <div>
                  <span className="text-[#64748B] block">Gap:</span>
                  <span className={`font-medium ${seniority.is_gap ? 'text-[#B45309]' : 'text-[#1E4D3A]'}`}>
                    {seniority.gap || (seniority.is_gap ? 'Unverified' : 'None')}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 7. Why This Matches (Evidence-Backed Statements) */}
      <div className="pt-4 border-t border-[#E2E2E2] space-y-3">
        <div
          className="text-xs font-bold uppercase tracking-wider text-[#1A1A1A]"
          aria-label="Why This Matches"
        >
          Why This Matches
        </div>

        <div className="space-y-2 text-xs text-[#4B5563] leading-relaxed">
          {analysis.strengths.length > 0 ? (
            analysis.strengths.map((str, idx) => (
              <div key={idx} className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#3D5580] mt-1.5 shrink-0" />
                <span>{str}</span>
              </div>
            ))
          ) : (
            <p className="text-[#94A3B8] italic">
              {isInsufficient
                ? 'Too few JD requirements were identified to generate verified strengths.'
                : 'No verified strengths to highlight based on the extracted requirements.'}
            </p>
          )}

          {/* Identified Gaps details */}
          {analysis.gaps.length > 0 && (
            <div className="pt-2 text-xs text-[#6B6B6B] space-y-1">
              <span className="font-semibold text-[#374151] block">Identified Gaps:</span>
              {analysis.gaps.map((gap, idx) => (
                <div key={idx} className="flex items-start gap-2 text-[#64748B]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#94A3B8] mt-1.5 shrink-0" />
                  <span>{gap}</span>
                </div>
              ))}
            </div>
          )}

          {analysis.relevant_projects.length > 0 && (
            <div className="mt-2.5 p-3 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="font-semibold text-[#1A1A1A] block mb-1">Demonstrated Projects:</span>
              <ul className="list-disc list-inside space-y-1 text-[#4B5563]">
                {analysis.relevant_projects.map((proj, idx) => (
                  <li key={idx} className="truncate">{proj}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

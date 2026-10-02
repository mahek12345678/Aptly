import { useState, useEffect, useId } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { Trash2, AlertCircle, ArrowRight, RefreshCw, FileText, Info } from 'lucide-react';
import { api } from '@/lib/api';
import { AnalyzeJDResponse } from '@/types/jd-analyzer';
import { RoleSummaryCard } from '@/components/analyzer/RoleSummaryCard';
import { MatchInsightsCard } from '@/components/analyzer/MatchInsightsCard';
import { ResumeTailoringCard } from '@/components/analyzer/ResumeTailoringCard';

export default function JDAnalyzerPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const textareaId = useId();

  const incomingCompany = location.state?.company || '';
  const incomingRole = location.state?.role_title || location.state?.roleTitle || '';
  const incomingDesc = location.state?.description || location.state?.jobDescription || '';
  const incomingSourceJobId = location.state?.source_job_id || location.state?.sourceJobId || null;

  const [jobDescription, setJobDescription] = useState<string>(incomingDesc);
  const [canonicalJob, setCanonicalJob] = useState<{ company?: string; role_title?: string; description?: string } | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisStage, setAnalysisStage] = useState<string>('Reading job description…');
  const [analysisResult, setAnalysisResult] = useState<AnalyzeJDResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [missingResumeError, setMissingResumeError] = useState(false);

  useEffect(() => {
    if (!incomingSourceJobId) return;

    let isMounted = true;
    api.get<any>(`/api/v1/jobs/${incomingSourceJobId}`)
      .then((data) => {
        if (!isMounted || !data) return;
        setCanonicalJob({
          company: data.company,
          role_title: data.role_title,
          description: data.description,
        });
        if (data.description) {
          setJobDescription((current) => {
            // Populate full canonical description if current is empty or shorter preview
            if (!current || current.length < data.description.length || data.description.startsWith(current)) {
              return data.description;
            }
            return current;
          });
        }
      })
      .catch((err) => {
        console.warn('Could not fetch canonical JobListing:', err);
      });

    return () => {
      isMounted = false;
    };
  }, [incomingSourceJobId]);

  const displayCompany = canonicalJob?.company || incomingCompany;
  const displayRole = canonicalJob?.role_title || incomingRole;

  const charCount = jobDescription.length;
  const isTooShort = jobDescription.trim().length < 20;
  const isTooLong = charCount > 30000;

  const handleClear = () => {
    setJobDescription('');
    setAnalysisResult(null);
    setErrorMessage(null);
    setMissingResumeError(false);
  };

  const handleAnalyze = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (isTooShort || isTooLong) return;

    setIsAnalyzing(true);
    setAnalysisStage('Reading job description…');
    setErrorMessage(null);
    setMissingResumeError(false);

    // Staged progression timer
    const t1 = setTimeout(() => setAnalysisStage('Extracting requirements…'), 700);
    const t2 = setTimeout(() => setAnalysisStage('Comparing resume evidence…'), 1800);
    const t3 = setTimeout(() => setAnalysisStage('Building recommendations…'), 3000);

    try {
      const response = await api.post<AnalyzeJDResponse>('/api/v1/jd/analyze', {
        job_description: jobDescription.trim(),
        source_job_id: incomingSourceJobId || null,
        company: displayCompany || null,
        role_title: displayRole || null,
      });
      setAnalysisResult(response);
    } catch (err: any) {
      const detail = err?.message || '';
      if (detail.toLowerCase().includes('no parsed resume') || detail.toLowerCase().includes('upload and parse')) {
        setMissingResumeError(true);
      } else {
        setErrorMessage(detail || "Aptly couldn't analyze this job right now. Please try again.");
      }
    } finally {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      setIsAnalyzing(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-5xl mx-auto pb-12">
        {/* Page Header */}
        <div>
          <h1 className="font-serif text-2xl sm:text-3xl font-bold text-[#1B2A4A] tracking-tight">
            JD Analyzer
          </h1>
          <p className="text-xs sm:text-sm text-[#6B6B6B] mt-1">
            Paste a full job description. Aptly extracts structured requirements, compares against your verified resume evidence, and suggests grounded tailoring.
          </p>
        </div>

        {/* Loaded from Find Positions context banner */}
        {(displayCompany || displayRole) && (
          <div className="px-4 py-2.5 rounded-xl bg-[#EBF3FA] border border-[#CBD5E1] text-[#1B2A4A] text-xs flex items-center justify-between animate-in fade-in duration-150">
            <div className="flex items-center gap-2">
              <span className="font-bold">Loaded for Analysis:</span>
              <span className="font-medium text-[#3D5580]">
                {displayCompany} {displayRole ? `— ${displayRole}` : ''}
              </span>
            </div>
            <span className="text-[11px] font-mono text-[#6B6B6B]">Find Positions Target</span>
          </div>
        )}

        {/* Missing Resume Warning Banner */}
        {missingResumeError && (
          <div className="p-4 sm:p-5 rounded-xl bg-[#FFFBEB] border border-[#FDE68A] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-in fade-in duration-200">
            <div className="flex items-start gap-3">
              <span className="p-2 rounded-lg bg-[#FEF3C7] text-[#B45309] shrink-0">
                <FileText size={18} aria-hidden="true" focusable="false" />
              </span>
              <div>
                <h4 className="text-xs font-bold text-[#92400E]">No parsed resume found</h4>
                <p className="text-xs text-[#B45309] mt-0.5 leading-relaxed">
                  Aptly needs your uploaded resume to calculate match scores and generate grounded tailoring suggestions.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => navigate('/onboarding/resume')}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#B45309] hover:bg-[#92400E] text-white text-xs font-semibold shrink-0 transition-colors shadow-xs"
            >
              <span>Upload Resume</span>
              <ArrowRight size={13} aria-hidden="true" focusable="false" />
            </button>
          </div>
        )}

        {/* General Error Banner */}
        {errorMessage && (
          <div className="p-4 rounded-xl bg-[#FEF2F2] border border-[#FCA5A5] text-[#991B1B] text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle size={16} className="shrink-0" aria-hidden="true" focusable="false" />
              <span>{errorMessage}</span>
            </div>
            <button
              type="button"
              onClick={() => setErrorMessage(null)}
              aria-label="Dismiss error"
              className="text-[#991B1B] hover:text-[#7F1D1D] font-bold text-sm ml-2 cursor-pointer"
            >
              ✕
            </button>
          </div>
        )}

        {/* Main JD Input Box */}
        <div className="p-5 sm:p-6 rounded-xl bg-white border border-[#E2E2E2] shadow-2xs space-y-4">
          <div className="flex items-center justify-between">
            <label
              htmlFor={textareaId}
              className="text-xs font-bold uppercase tracking-wider text-[#1B2A4A] flex items-center gap-1.5"
            >
              <FileText size={14} className="text-[#3D5580]" aria-hidden="true" focusable="false" />
              <span>Job Description</span>
            </label>

            <div className="flex items-center gap-3">
              <span className="text-[11px] text-[#9CA3AF] font-mono">
                {charCount.toLocaleString()} / 30,000 chars
              </span>
              {jobDescription && (
                <button
                  type="button"
                  onClick={handleClear}
                  disabled={isAnalyzing}
                  aria-label="Clear job description"
                  className="inline-flex items-center gap-1 text-[11px] text-[#6B6B6B] hover:text-[#991B1B] transition-colors cursor-pointer"
                >
                  <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                    <Trash2 size={12} aria-hidden="true" focusable="false" />
                  </span>
                  <span>Clear</span>
                </button>
              )}
            </div>
          </div>

          <textarea
            id={textareaId}
            rows={10}
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            disabled={isAnalyzing}
            placeholder="Paste the complete job description here (up to 30,000 characters). Aptly automatically strips aggregator boilerplate and extracts real qualifications."
            className="w-full p-3.5 text-xs sm:text-sm rounded-lg border border-[#E2E2E2] focus:border-[#1B2A4A] focus:outline-none focus:ring-1 focus:ring-[#1B2A4A] bg-[#FAFAFA] text-[#1A1A1A] placeholder:text-[#9CA3AF] resize-y leading-relaxed font-sans"
          />

          {isTooLong && (
            <p className="text-[11px] text-[#B91C1C]">
              Job description exceeds 30,000 characters. Please trim extraneous appendices or disclaimers.
            </p>
          )}

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
            <p className="text-[11px] text-[#6B6B6B]">
              Tip: Include the full text including requirements and qualifications near the end of the JD.
            </p>

            <button
              type="button"
              onClick={() => handleAnalyze()}
              disabled={isTooShort || isTooLong || isAnalyzing}
              aria-label="Analyze job description"
              className="inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg bg-[#1B2A4A] hover:bg-[#142038] text-white text-xs sm:text-sm font-semibold transition-colors shadow-xs disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98] cursor-pointer"
            >
              {isAnalyzing ? (
                <>
                  <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                    <RefreshCw size={14} className="animate-spin" aria-hidden="true" focusable="false" />
                  </span>
                  <span>{analysisStage}</span>
                </>
              ) : (
                <span>Analyze job</span>
              )}
            </button>
          </div>
        </div>

        {/* Loading Progress State */}
        {isAnalyzing && (
          <div className="p-8 sm:p-12 rounded-xl bg-white border border-[#E2E2E2] text-center space-y-4 animate-in fade-in duration-200">
            <div className="w-12 h-12 rounded-2xl bg-[#F0F4F8] text-[#1B2A4A] flex items-center justify-center mx-auto border border-[#D5DEE8]">
              <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                <RefreshCw size={22} className="animate-spin text-[#3D5580]" aria-hidden="true" focusable="false" />
              </span>
            </div>
            <div>
              <h3 className="font-serif text-base sm:text-lg font-bold text-[#1B2A4A]">
                {analysisStage}
              </h3>
              <p className="text-xs text-[#6B6B6B] mt-1 max-w-sm mx-auto leading-relaxed">
                Cleaning third-party boilerplate, extracting structured requirements, and computing deterministic evidence matching against your resume.
              </p>
            </div>
            <div className="w-48 h-1 bg-[#E2E2E2] rounded-full mx-auto overflow-hidden relative">
              <div className="w-1/2 h-full bg-[#1B2A4A] rounded-full animate-pulse" />
            </div>
          </div>
        )}

        {/* Limited / Partial JD Quality Warning */}
        {!isAnalyzing && analysisResult && (
          analysisResult.job_details?.description_quality === 'PARTIAL' ||
          analysisResult.job_details?.analysis_quality === 'insufficient_job_description' ||
          analysisResult.match_analysis?.analysis_quality === 'INSUFFICIENT_REQUIREMENTS' ||
          analysisResult.match_analysis?.analysis_quality === 'PARTIAL'
        ) && (
          <div className="p-5 rounded-xl bg-[#FFFBEB] border border-[#FDE68A] text-[#92400E] space-y-3 animate-in fade-in duration-200">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 font-bold text-xs">
                <span aria-hidden="true" className="inline-flex shrink-0 select-none">
                  <Info size={16} className="text-[#B45309]" aria-hidden="true" focusable="false" />
                </span>
                <span>LIMITED JOB DESCRIPTION</span>
              </div>
              <button
                type="button"
                onClick={() => {
                  const el = document.getElementById(textareaId);
                  if (el) {
                    el.focus();
                    (el as HTMLTextAreaElement).select();
                    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                  }
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#B45309] hover:bg-[#92400E] text-white text-xs font-semibold shrink-0 transition-colors shadow-xs cursor-pointer"
              >
                <span>Paste full JD</span>
              </button>
            </div>
            <p className="text-xs leading-relaxed text-[#B45309]">
              {analysisResult.job_details.quality_warning ||
                "Your job provider supplied a shortened description. Paste the full job description for the most reliable analysis."}
            </p>
            <p className="text-[11px] text-[#92400E] font-medium border-t border-[#FDE68A]/60 pt-2">
              Paste the complete description from the employer's job page. Aptly will use your pasted version for this analysis.
            </p>
          </div>
        )}

        {/* Results Sections */}
        {!isAnalyzing && analysisResult && analysisResult.job_details?.analysis_quality !== 'insufficient_job_description' && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {/* 1. Role Summary */}
            <RoleSummaryCard
              job={analysisResult.job_details}
              rawJd={jobDescription}
              applicationUrl={location.state?.applicationUrl || analysisResult.job_details.application_url}
              sourceJobId={incomingSourceJobId || analysisResult.job_details.source_job_id}
            />

            {/* 2. Match Score & Skills Insights */}
            <MatchInsightsCard
              analysis={analysisResult.match_analysis}
              resumeFilename={analysisResult.resume_filename}
            />

            {/* 3. Resume Tailoring Engine */}
            <ResumeTailoringCard
              resumeId={analysisResult.resume_id}
              rawJd={jobDescription}
              sourceJobId={incomingSourceJobId || analysisResult.job_details.source_job_id}
              company={incomingCompany || analysisResult.job_details.company}
              roleTitle={incomingRole || analysisResult.job_details.role_title}
            />
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

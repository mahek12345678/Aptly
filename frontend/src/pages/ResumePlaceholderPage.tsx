import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, CheckCircle2, FileText, Trash2, Shield, Loader2, AlertCircle } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/lib/api';
import OnboardingHeader from '@/components/OnboardingHeader';
import OnboardingStepper from '@/components/OnboardingStepper';
import resumeUploadIllustration from '@/assets/resume-upload-illustration.png';

// ---------------------------------------------------------------------------
// Custom Icons (Pixel-matched with Reference Image 2)
// ---------------------------------------------------------------------------

function GoogleDriveIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="shrink-0">
      <path
        d="M8.01 2.5L0.5 15.5H7.72L15.23 2.5H8.01Z"
        fill="#00AC47"
      />
      <path
        d="M15.99 2.5H8.01L15.52 15.5H23.5L15.99 2.5Z"
        fill="#2684FC"
      />
      <path
        d="M23.5 15.5H8.97L5.21 22H19.74L23.5 15.5Z"
        fill="#FFBA00"
      />
      <path
        d="M0.5 15.5L4.26 22H18.79L15.03 15.5H0.5Z"
        fill="#EA4335"
      />
      {/* Accurate 3-stripe overlay */}
      <path
        d="M7.72 15.5H0.5L4.26 22L8.02 15.5H7.72Z"
        fill="#0066DA"
      />
      <path
        d="M15.23 2.5L7.72 15.5H15.52L23.03 2.5H15.23Z"
        fill="#00832D"
      />
    </svg>
  );
}

function RobotAssistantAvatar() {
  return (
    <div className="relative w-16 h-16 sm:w-18 sm:h-18 shrink-0 select-none">
      <svg viewBox="0 0 100 100" className="w-full h-full drop-shadow-sm">
        <defs>
          <linearGradient id="botHeadGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#FFFFFF" />
            <stop offset="60%" stopColor="#F1F5F9" />
            <stop offset="100%" stopColor="#E2E8F0" />
          </linearGradient>
          <linearGradient id="botScreenGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#0B132B" />
            <stop offset="100%" stopColor="#1C2541" />
          </linearGradient>
          <linearGradient id="botEarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#E2E8F0" />
            <stop offset="100%" stopColor="#94A3B8" />
          </linearGradient>
          <filter id="botGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="1.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Neck / Base */}
        <path d="M40 76 Q50 82 60 76 L62 84 Q50 90 38 84 Z" fill="#CBD5E1" />
        <ellipse cx="50" cy="85" rx="16" ry="5" fill="#E2E8F0" />

        {/* Left Ear / Antenna node */}
        <circle cx="21" cy="48" r="7" fill="url(#botEarGrad)" />
        <circle cx="21" cy="48" r="4" fill="#3B82F6" />

        {/* Right Ear / Antenna node */}
        <circle cx="79" cy="48" r="7" fill="url(#botEarGrad)" />
        <circle cx="79" cy="48" r="4" fill="#3B82F6" />

        {/* Head Shell */}
        <rect
          x="22"
          y="20"
          width="56"
          height="54"
          rx="26"
          fill="url(#botHeadGrad)"
          stroke="#CBD5E1"
          strokeWidth="1.2"
        />

        {/* Antenna top tip */}
        <path d="M50 20 L50 12" stroke="#94A3B8" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx="50" cy="11" r="3.5" fill="#3B82F6" />

        {/* Face Screen */}
        <rect
          x="30"
          y="32"
          width="40"
          height="30"
          rx="12"
          fill="url(#botScreenGrad)"
        />

        {/* Left Eye (Smiling Curve) */}
        <path
          d="M37 45 Q41 40 45 45"
          fill="none"
          stroke="#60A5FA"
          strokeWidth="2.8"
          strokeLinecap="round"
          filter="url(#botGlow)"
        />

        {/* Right Eye (Smiling Curve) */}
        <path
          d="M55 45 Q59 40 63 45"
          fill="none"
          stroke="#60A5FA"
          strokeWidth="2.8"
          strokeLinecap="round"
          filter="url(#botGlow)"
        />

        {/* Cute Smile Line */}
        <path
          d="M47 52 Q50 55 53 52"
          fill="none"
          stroke="#93C5FD"
          strokeWidth="1.8"
          strokeLinecap="round"
        />

        {/* Glossy Top Reflection */}
        <ellipse cx="44" cy="27" rx="14" ry="4" fill="#FFFFFF" opacity="0.6" />
      </svg>
    </div>
  );
}

function ExtractKeyInfoIcon() {
  return (
    <div className="w-8 h-8 rounded-lg bg-[#F0F5FA] flex items-center justify-center shrink-0 text-[#2B62C6]">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <line x1="10" y1="9" x2="8" y2="9" />
      </svg>
    </div>
  );
}

function MatchOpportunitiesIcon() {
  return (
    <div className="w-8 h-8 rounded-lg bg-[#F0F5FA] flex items-center justify-center shrink-0 text-[#2B62C6]">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <circle cx="12" cy="12" r="6" />
        <circle cx="12" cy="12" r="2" />
      </svg>
    </div>
  );
}

function TailorResumeIcon() {
  return (
    <div className="w-8 h-8 rounded-lg bg-[#F0F5FA] flex items-center justify-center shrink-0 text-[#2B62C6]">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
      </svg>
    </div>
  );
}

function ImproveRecommendationsIcon() {
  return (
    <div className="w-8 h-8 rounded-lg bg-[#F0F5FA] flex items-center justify-center shrink-0 text-[#2B62C6]">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="18" y1="20" x2="18" y2="10" />
        <line x1="12" y1="20" x2="12" y2="4" />
        <line x1="6" y1="20" x2="6" y2="14" />
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Resume Page Component
// ---------------------------------------------------------------------------

interface UploadedResume {
  id: string;
  file_name: string;
  file_size_bytes?: number | null;
  file_size?: number | null;
  parsed_status: string;
  created_at: string;
}

function formatFileSize(bytes?: number | null): string {
  if (!bytes || bytes === 0) return '0 KB';
  const kb = bytes / 1024;
  if (kb < 1024) {
    return `${kb.toFixed(1)} KB`;
  }
  const mb = kb / 1024;
  return `${mb.toFixed(2)} MB`;
}

export default function ResumePlaceholderPage() {
  const navigate = useNavigate();
  const { updateOnboardingProgress } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Resume & API state
  const [uploadedResume, setUploadedResume] = useState<UploadedResume | null>(null);
  const [isLoadingInitial, setIsLoadingInitial] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFileName, setSelectedFileName] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Drag & notifications
  const [dragActive, setDragActive] = useState(false);
  const [driveNotification, setDriveNotification] = useState<string | null>(null);

  // Load existing active resume on mount
  useEffect(() => {
    let isMounted = true;
    api
      .get<UploadedResume>('/api/resumes/current')
      .then((data) => {
        if (!isMounted) return;
        if (data && data.id) {
          setUploadedResume(data);
        }
      })
      .catch(() => {
        // 404 is expected when no resume has been uploaded yet
      })
      .finally(() => {
        if (isMounted) setIsLoadingInitial(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const uploadFile = async (file: File) => {
    setErrorMessage(null);
    setDriveNotification(null);

    // Validate extension
    const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
    if (ext !== '.pdf' && ext !== '.docx') {
      setErrorMessage('Please upload a valid PDF or DOCX file.');
      return;
    }

    // Validate size (10 MB max)
    if (file.size > 10 * 1024 * 1024) {
      setErrorMessage('File size exceeds the 10 MB limit. Please upload a smaller file.');
      return;
    }

    if (file.size === 0) {
      setErrorMessage('The selected file is empty.');
      return;
    }

    // Distinguish between file selected (not yet uploaded) and successfully uploaded
    setSelectedFileName(file.name);
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);
      const data = await api.upload<UploadedResume>('/api/resumes/upload', formData);
      setUploadedResume(data);
      setSelectedFileName('');
      setErrorMessage(null);

      // Immediately trigger deterministic parse & vector embedding extraction
      try {
        const parsed = await api.post<UploadedResume>(`/api/resumes/${data.id}/parse`);
        setUploadedResume(parsed);
      } catch (parseErr) {
        console.warn('Resume parsing notice:', parseErr);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed. Please try again.';
      setErrorMessage(msg);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      uploadFile(file);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      uploadFile(file);
    }
  };

  const handleGoogleDriveClick = () => {
    setDriveNotification('Select your downloaded Google Drive resume (PDF or DOCX):');
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleRemove = async () => {
    if (!uploadedResume || isDeleting) return;
    setIsDeleting(true);
    setErrorMessage(null);
    try {
      await api.delete('/api/resumes/current');
      setUploadedResume(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to remove resume.';
      setErrorMessage(msg);
    } finally {
      setIsDeleting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleContinue = async () => {
    if (!uploadedResume || isSubmitting) return;
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      if (uploadedResume.parsed_status !== 'parsed') {
        try {
          await api.post(`/api/resumes/${uploadedResume.id}/parse`);
        } catch (e) {
          console.warn('Resume parse warning on continue:', e);
        }
      }
      await api.put('/api/onboarding/step', { step: 3 });
      await updateOnboardingProgress(3);

      setIsTransitioning(true);
      setTimeout(() => {
        navigate('/onboarding/personalize');
      }, 300);
    } catch (err: unknown) {
      setIsSubmitting(false);
      const errDetail =
        err instanceof Error ? err.message : 'Unable to proceed. Please try again.';
      setErrorMessage(errDetail);
    }
  };

  const handleBack = () => {
    navigate('/onboarding');
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col font-inter text-[#1A1A1A] selection:bg-[#2B62C6]/15">
      {/* Header */}
      <OnboardingHeader />

      {/* Main Content Area with transition animations */}
      <main
        className={`flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 flex flex-col ${
          isTransitioning ? 'animate-slide-left-out' : 'animate-slide-up'
        }`}
      >
        {/* Stepper (Step 1=Completed, Step 2=Active, Step 3=Upcoming, Step 4=Upcoming) */}
        <div className="mb-8 sm:mb-10">
          <OnboardingStepper currentStep={2} />
        </div>

        {/* 2-Column Main Section (Desktop: Two Columns, Mobile: Stacked) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start">
          {/* ============================================================== */}
          {/* LEFT COLUMN: Main Upload Area (7 cols on lg, 8 on xl)          */}
          {/* ============================================================== */}
          <div className="lg:col-span-7 xl:col-span-8 flex flex-col">
            {/* Main Heading & Subtext */}
            <div className="mb-5 sm:mb-6">
              <h1 className="font-serif text-[28px] sm:text-[32px] lg:text-[34px] font-bold text-[#111827] tracking-tight leading-tight">
                Upload your resume
              </h1>
              <p className="text-[13.5px] sm:text-[14px] text-[#64748B] mt-1 font-normal">
                We support PDF (recommended), DOCX up to 10 MB.
              </p>
            </div>

            {/* Error Message Alert (State 5: Error) */}
            {errorMessage && (
              <div className="mb-4 p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-start gap-2.5 animate-fade-in">
                <AlertCircle size={16} className="shrink-0 mt-0.5 text-red-500" />
                <div className="flex-1">
                  <p className="font-medium">{errorMessage}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setErrorMessage(null)}
                  className="text-red-400 hover:text-red-600 font-bold px-1 transition-colors cursor-pointer"
                  aria-label="Dismiss error"
                >
                  &times;
                </button>
              </div>
            )}

            {/* Dashed Dropzone Box */}
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`w-full rounded-2xl border-2 border-dashed transition-all duration-200 p-6 sm:p-8 flex flex-col items-center justify-center text-center relative ${
                dragActive
                  ? 'border-[#2B62C6] bg-[#F0F6FD]'
                  : uploadedResume
                  ? 'border-[#CBD5E1] bg-white'
                  : 'border-[#CBD5E1] bg-white hover:border-[#94A3B8] hover:bg-[#F8FAFC]'
              }`}
              style={{ minHeight: '340px' }}
            >
              {isLoadingInitial ? (
                /* Initial loading check state */
                <div className="flex flex-col items-center justify-center py-10 animate-fade-in">
                  <Loader2 size={32} className="text-[#2B62C6] animate-spin" />
                  <p className="text-[13px] text-[#64748B] mt-3 font-medium">Checking saved resume...</p>
                </div>
              ) : isUploading ? (
                /* State: Uploading state */
                <div className="flex flex-col items-center justify-center py-8 animate-fade-in">
                  <div className="w-16 h-16 rounded-2xl bg-[#EBF3FC] flex items-center justify-center mb-4">
                    <Loader2 size={32} className="text-[#2B62C6] animate-spin" />
                  </div>
                  <p className="text-[15px] font-bold text-[#111827]">
                    Uploading your resume...
                  </p>
                  {selectedFileName && (
                    <p className="text-[12.5px] text-[#64748B] mt-1 max-w-sm truncate px-4">
                      {selectedFileName}
                    </p>
                  )}
                  <p className="text-[11.5px] text-[#94A3B8] mt-2">
                    Please wait while we securely store your file
                  </p>
                </div>
              ) : uploadedResume ? (
                /* State: Uploaded Successfully */
                <div className="w-full py-4 animate-fade-in flex flex-col items-center">
                  <div className="w-14 h-14 rounded-2xl bg-[#EBF3FC] text-[#2B62C6] flex items-center justify-center mb-3">
                    <FileText size={28} />
                  </div>

                  <p
                    className="text-[15px] font-bold text-[#111827] max-w-sm truncate px-2"
                    title={uploadedResume.file_name}
                  >
                    {uploadedResume.file_name}
                  </p>

                  <p className="text-[12px] text-[#64748B] mt-0.5">
                    {formatFileSize(uploadedResume.file_size_bytes ?? uploadedResume.file_size)}
                  </p>

                  <div className="inline-flex items-center gap-1.5 text-xs text-emerald-600 font-medium bg-emerald-50 px-3 py-1 rounded-full border border-emerald-100 mt-3 mb-2">
                    <CheckCircle2 size={13} />
                    <span>Resume uploaded successfully</span>
                  </div>

                  <div className="flex items-center gap-3 mt-2">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={isDeleting || isUploading}
                      className="px-4 py-1.5 rounded-lg border border-[#CBD5E1] bg-white hover:bg-slate-50 active:bg-slate-100 text-xs font-medium text-[#334155] transition-colors cursor-pointer disabled:opacity-50"
                    >
                      Replace
                    </button>
                    <button
                      type="button"
                      onClick={handleRemove}
                      disabled={isDeleting || isUploading}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium text-red-600 hover:bg-red-50 active:bg-red-100 flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
                    >
                      {isDeleting ? (
                        <>
                          <Loader2 size={13} className="animate-spin" />
                          <span>Removing…</span>
                        </>
                      ) : (
                        <>
                          <Trash2 size={13} />
                          <span>Remove</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ) : (
                /* State 1: Empty Upload State (and State 2: Drag-Over) */
                <>
                  {/* Centered Upload Illustration */}
                  <div className="w-full max-w-[210px] sm:max-w-[240px] h-[150px] sm:h-[165px] flex items-center justify-center pointer-events-none select-none mb-2">
                    <img
                      src={resumeUploadIllustration}
                      alt="Upload resume illustration"
                      className="w-full h-full object-contain"
                      draggable={false}
                    />
                  </div>

                  {/* Drag & Drop prompt */}
                  <p className="text-[15px] sm:text-[16px] font-bold text-[#111827] leading-snug">
                    Drag &amp; drop your resume here
                  </p>

                  {/* Small "or" */}
                  <span className="text-[12px] text-[#64748B] my-1.5 font-medium">or</span>

                  {/* Choose File Button */}
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="px-6 py-2 rounded-lg border border-[#CBD5E1] bg-[#F8FAFC] hover:bg-[#F1F5F9] active:bg-[#E2E8F0] text-[#1E3A8A] font-medium text-[13px] sm:text-[13.5px] transition-colors shadow-xs cursor-pointer"
                  >
                    Choose file
                  </button>

                  {/* File format & limit note */}
                  <p className="text-[11.5px] text-[#64748B] mt-2.5">
                    PDF, DOCX (Max 10 MB)
                  </p>
                </>
              )}

              {/* Hidden HTML File Input */}
              <input
                ref={fileInputRef}
                id="resume-file-input"
                type="file"
                accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={handleFileChange}
                className="hidden"
              />
            </div>

            {/* Divider with "or" */}
            <div className="relative flex items-center justify-center my-3.5 sm:my-4">
              <div className="w-full border-t border-[#E2E8F0]" />
              <span className="absolute bg-[#FAFAFA] px-3 text-[12px] text-[#64748B] font-medium select-none">
                or
              </span>
            </div>

            {/* Import from Google Drive Button */}
            <button
              type="button"
              onClick={handleGoogleDriveClick}
              disabled={isUploading || isDeleting}
              className="w-full h-[44px] rounded-xl bg-[#F0F4F9] hover:bg-[#E5EDF7] active:bg-[#DBE5F2] border border-[#E2E8F0] text-[#1E3A8A] font-medium text-[13.5px] flex items-center justify-center gap-2.5 transition-colors shadow-xs cursor-pointer select-none disabled:opacity-50"
            >
              <GoogleDriveIcon />
              <span>Import from Google Drive</span>
            </button>

            {driveNotification && (
              <p className="mt-2 text-xs text-blue-800 text-center animate-fade-in">
                {driveNotification}
              </p>
            )}
          </div>

          {/* ============================================================== */}
          {/* RIGHT COLUMN: AI Assistant & What Happens Next Panel (5 cols)  */}
          {/* ============================================================== */}
          <div className="lg:col-span-5 xl:col-span-4 flex flex-col">
            <div className="w-full bg-white rounded-2xl border border-[#E2E8F0] overflow-hidden shadow-xs">
              {/* Top AI Speech Bubble Section */}
              <div className="bg-[#F0F6FD] p-5 sm:p-6 border-b border-[#E2E8F0]/70 flex items-center gap-4">
                <RobotAssistantAvatar />
                <p className="font-handwriting text-[15px] sm:text-[16px] text-[#24416B] leading-snug select-none">
                  I’ll analyze your resume and extract the important details for you.
                </p>
              </div>

              {/* Body Section: What happens next? */}
              <div className="p-5 sm:p-6">
                <h2 className="text-[14px] font-bold text-[#111827] mb-3.5">
                  What happens next?
                </h2>

                <div className="space-y-3.5">
                  {/* Item 1 */}
                  <div className="flex items-start gap-3">
                    <ExtractKeyInfoIcon />
                    <div className="pt-0.5">
                      <p className="text-[13px] font-medium text-[#1E293B] leading-tight">
                        Extract key information
                      </p>
                      <p className="text-[11.5px] text-[#64748B] mt-0.5 leading-snug">
                        (education, skills, experience, projects)
                      </p>
                    </div>
                  </div>

                  {/* Item 2 */}
                  <div className="flex items-start gap-3">
                    <MatchOpportunitiesIcon />
                    <div className="pt-1">
                      <p className="text-[13px] font-medium text-[#1E293B] leading-tight">
                        Match you with relevant opportunities
                      </p>
                    </div>
                  </div>

                  {/* Item 3 */}
                  <div className="flex items-start gap-3">
                    <TailorResumeIcon />
                    <div className="pt-1">
                      <p className="text-[13px] font-medium text-[#1E293B] leading-tight">
                        Help tailor your resume for specific jobs
                      </p>
                    </div>
                  </div>

                  {/* Item 4 */}
                  <div className="flex items-start gap-3">
                    <ImproveRecommendationsIcon />
                    <div className="pt-1">
                      <p className="text-[13px] font-medium text-[#1E293B] leading-tight">
                        Improve recommendations over time
                      </p>
                    </div>
                  </div>
                </div>

                {/* Divider */}
                <div className="border-t border-[#E2E8F0] my-4" />

                {/* Privacy subsection */}
                <div className="flex items-start gap-2.5 text-[#64748B]">
                  <Shield size={18} className="shrink-0 mt-0.5 text-[#64748B]" />
                  <div className="text-[11.5px] text-[#64748B] leading-relaxed">
                    <p className="font-medium text-[#475569]">Your data is private and secure.</p>
                    <p className="mt-0.5">We never share your resume without your permission.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ============================================================== */}
        {/* BOTTOM NAVIGATION: Back & Continue Buttons                    */}
        {/* ============================================================== */}
        <div className="mt-8 pt-6 flex items-center justify-between">
          {/* Back button */}
          <button
            type="button"
            onClick={handleBack}
            className="px-5 py-2.5 rounded-xl border border-[#CBD5E1] bg-white hover:bg-[#F8FAFC] active:bg-[#F1F5F9] text-[13.5px] font-medium text-[#334155] flex items-center gap-2 transition-colors shadow-xs cursor-pointer"
          >
            <ArrowLeft size={16} />
            <span>Back</span>
          </button>

          {/* Continue button: disabled until a resume exists */}
          <button
            id="resume-continue-btn"
            type="button"
            onClick={handleContinue}
            disabled={!uploadedResume || isUploading || isDeleting || isSubmitting || isLoadingInitial}
            className="min-w-[140px] px-7 py-2.5 rounded-xl bg-[#234C8E] hover:bg-[#1C3E75] active:bg-[#16305C] text-white font-medium text-[13.5px] flex items-center justify-center gap-2 shadow-sm hover:shadow transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={15} className="animate-spin" />
                <span>Saving…</span>
              </>
            ) : (
              <>
                <span>Continue</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </div>
      </main>
    </div>
  );
}

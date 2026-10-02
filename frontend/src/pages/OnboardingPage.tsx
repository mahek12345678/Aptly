import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  GraduationCap,
  Briefcase,
  FileText,
  Building2,
  ShieldCheck,
  ArrowRight,
  ChevronDown,
  Loader2,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import OnboardingHeader from '@/components/OnboardingHeader';
import OnboardingStepper from '@/components/OnboardingStepper';
import TagInput from '@/components/TagInput';

// Pre-defined graduation year options
const GRAD_YEARS = [2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031];

// Quick location pills
const LOCATION_OPTIONS = ['Remote', 'On-site', 'Hybrid'];

export default function OnboardingPage() {
  const navigate = useNavigate();
  const { updateOnboardingProgress } = useAuth();

  // Form state
  const [userType, setUserType] = useState<'student' | 'professional'>('student');
  const [opportunityType, setOpportunityType] = useState<'internship' | 'full_time'>('internship');
  const [graduationYear, setGraduationYear] = useState<number>(2026);
  const [preferredLocation, setPreferredLocation] = useState<string>('Remote');
  const [customLocationInput, setCustomLocationInput] = useState<string>('');
  const [preferredRoles, setPreferredRoles] = useState<string[]>([]);
  const [interests, setInterests] = useState<string[]>([]);

  // UI state
  const [loadingExisting, setLoadingExisting] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch existing preferences on mount
  useEffect(() => {
    let isMounted = true;
    api
      .get<{
        user_type?: string;
        opportunity_type?: string;
        graduation_year?: number;
        preferred_location?: string;
        preferred_roles?: string[];
        interests?: string[];
      }>('/api/onboarding/preferences')
      .then((data) => {
        if (!isMounted || !data) return;
        if (data.user_type === 'student' || data.user_type === 'professional') {
          setUserType(data.user_type);
        }
        if (data.opportunity_type === 'internship' || data.opportunity_type === 'full_time') {
          setOpportunityType(data.opportunity_type);
        }
        if (data.graduation_year) {
          setGraduationYear(data.graduation_year);
        }
        if (data.preferred_location) {
          setPreferredLocation(data.preferred_location);
          if (!LOCATION_OPTIONS.includes(data.preferred_location)) {
            setCustomLocationInput(data.preferred_location);
          }
        }
        if (Array.isArray(data.preferred_roles)) {
          setPreferredRoles(data.preferred_roles);
        }
        if (Array.isArray(data.interests)) {
          setInterests(data.interests);
        }
      })
      .catch(() => {
        // First time onboarding - ignore error and keep defaults
      })
      .finally(() => {
        if (isMounted) setLoadingExisting(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const handleLocationSelect = (loc: string) => {
    setPreferredLocation(loc);
  };

  const handleContinue = async () => {
    setErrorMessage(null);
    setIsSubmitting(true);

    const payload = {
      user_type: userType,
      opportunity_type: opportunityType,
      graduation_year: userType === 'student' ? graduationYear : null,
      preferred_location: preferredLocation,
      preferred_roles: preferredRoles,
      interests: interests,
    };

    try {
      // Save locally
      localStorage.setItem('aptly_onboarding_step1', JSON.stringify(payload));

      // Persist to backend
      await api.put('/api/onboarding/preferences', payload);
      await updateOnboardingProgress(2);

      // Trigger exit animation
      setIsTransitioning(true);

      // Navigate after transition completes
      setTimeout(() => {
        navigate('/onboarding/resume');
      }, 300);
    } catch (err: unknown) {
      setIsSubmitting(false);
      const errDetail =
        err instanceof Error ? err.message : 'Unable to save preferences. Please try again.';
      setErrorMessage(errDetail);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col font-inter text-[#1A1A1A]">
      {/* Top Header */}
      <OnboardingHeader />

      {/* Main Content Container */}
      <div className="flex-1 flex flex-col lg:flex-row w-full max-w-[1440px] mx-auto">
        {/* Left Panel */}
        <aside className="w-full lg:w-[380px] xl:w-[420px] bg-white lg:bg-[#F9FAFB] border-b lg:border-b-0 lg:border-r border-border/80 p-6 sm:p-8 lg:p-10 xl:p-12 flex flex-col justify-between animate-fade-in shrink-0">
          <div className="space-y-6">
            {/* Step Counter */}
            <span className="text-[11px] font-bold tracking-[0.18em] uppercase text-[#64748B]">
              STEP 1 OF 4
            </span>

            {/* Editorial Heading */}
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#0F172A] font-serif-editorial leading-[1.12]">
              Let’s set up
              <br />
              your workspace.
            </h1>

            {/* Supporting Copy */}
            <p className="text-sm text-[#475569] leading-relaxed font-normal">
              A few quick details to help Aptly find the most relevant opportunities and tailor
              everything for you.
            </p>

            {/* Catchphrase */}
            <div className="pt-4">
              <p className="font-serif-editorial italic text-base sm:text-lg text-[#334155] leading-snug">
                Good careers are built
                <br />
                with clarity.
              </p>
              <div className="w-6 h-[1.5px] bg-[#94A3B8] mt-3" />
            </div>
          </div>

          <div className="hidden lg:block pt-8 border-t border-border/60">
            <p className="text-[11.5px] text-[#64748B] leading-relaxed">
              Step 1 of your tailored onboarding &bull; Your details are kept private and secure.
            </p>
          </div>
        </aside>

        {/* Right Main Form Area */}
        <main
          className={`flex-1 p-6 sm:p-10 lg:p-12 xl:p-14 max-w-4xl transition-all duration-300 ${
            isTransitioning ? 'animate-slide-left-out' : 'animate-slide-up'
          }`}
        >
          {/* Stepper */}
          <div className="mb-8 sm:mb-10">
            <OnboardingStepper currentStep={1} />
          </div>

          {/* Form Header */}
          <div className="mb-8">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#0F172A] font-serif-editorial">
              Tell us about yourself
            </h2>
            <p className="text-sm text-[#64748B] mt-1.5 font-normal">
              This helps us personalize your job matches and recommendations.
            </p>
          </div>

          {errorMessage && (
            <div className="mb-6 p-3.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
              {errorMessage}
            </div>
          )}

          {/* Form Fields Grid */}
          <div className="space-y-7">
            {/* Row 1: "I am a" & "Expected graduation year" */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Field: I am a */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#334155] mb-2.5">
                  I am a
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* Option 1: Student */}
                  <button
                    type="button"
                    onClick={() => setUserType('student')}
                    className={`relative p-3.5 sm:p-4 rounded-xl border text-left flex flex-col justify-between transition-all duration-200 focus:outline-none ${
                      userType === 'student'
                        ? 'border-[#1B2A4A] bg-[#F4F7FB] shadow-sm ring-1 ring-[#1B2A4A]'
                        : 'border-[#E2E8F0] bg-white hover:border-[#CBD5E1] hover:bg-slate-50/50'
                    }`}
                  >
                    <div className="flex items-start justify-between w-full mb-3">
                      <div
                        className={`w-9 h-9 rounded-lg flex items-center justify-center transition-colors ${
                          userType === 'student'
                            ? 'bg-[#1B2A4A] text-white'
                            : 'bg-[#F1F5F9] text-[#475569]'
                        }`}
                      >
                        <GraduationCap size={18} strokeWidth={2.2} />
                      </div>
                      <div
                        className={`w-4 h-4 rounded-full border flex items-center justify-center transition-all ${
                          userType === 'student'
                            ? 'border-[#1B2A4A] bg-[#1B2A4A]'
                            : 'border-[#CBD5E1] bg-white'
                        }`}
                      >
                        {userType === 'student' && (
                          <div className="w-1.5 h-1.5 rounded-full bg-white" />
                        )}
                      </div>
                    </div>
                    <div>
                      <span className="block text-sm font-semibold text-[#0F172A]">Student</span>
                      <span className="block text-[11px] text-[#64748B] mt-0.5 leading-snug">
                        Currently pursuing a degree
                      </span>
                    </div>
                  </button>

                  {/* Option 2: Working Professional */}
                  <button
                    type="button"
                    onClick={() => setUserType('professional')}
                    className={`relative p-3.5 sm:p-4 rounded-xl border text-left flex flex-col justify-between transition-all duration-200 focus:outline-none ${
                      userType === 'professional'
                        ? 'border-[#1B2A4A] bg-[#F4F7FB] shadow-sm ring-1 ring-[#1B2A4A]'
                        : 'border-[#E2E8F0] bg-white hover:border-[#CBD5E1] hover:bg-slate-50/50'
                    }`}
                  >
                    <div className="flex items-start justify-between w-full mb-3">
                      <div
                        className={`w-9 h-9 rounded-lg flex items-center justify-center transition-colors ${
                          userType === 'professional'
                            ? 'bg-[#1B2A4A] text-white'
                            : 'bg-[#F1F5F9] text-[#475569]'
                        }`}
                      >
                        <Briefcase size={18} strokeWidth={2.2} />
                      </div>
                      <div
                        className={`w-4 h-4 rounded-full border flex items-center justify-center transition-all ${
                          userType === 'professional'
                            ? 'border-[#1B2A4A] bg-[#1B2A4A]'
                            : 'border-[#CBD5E1] bg-white'
                        }`}
                      >
                        {userType === 'professional' && (
                          <div className="w-1.5 h-1.5 rounded-full bg-white" />
                        )}
                      </div>
                    </div>
                    <div>
                      <span className="block text-sm font-semibold text-[#0F172A]">
                        Working Professional
                      </span>
                      <span className="block text-[11px] text-[#64748B] mt-0.5 leading-snug">
                        Actively working (full-time/part-time)
                      </span>
                    </div>
                  </button>
                </div>
              </div>

              {/* Field: Expected graduation year */}
              <div>
                <label
                  htmlFor="graduation-year-select"
                  className="block text-xs font-semibold uppercase tracking-wider text-[#334155] mb-2.5"
                >
                  Expected graduation year
                </label>
                <div className="relative">
                  <select
                    id="graduation-year-select"
                    value={graduationYear}
                    onChange={(e) => setGraduationYear(Number(e.target.value))}
                    disabled={userType !== 'student'}
                    className={`w-full h-[52px] px-4 py-2.5 bg-white border rounded-xl appearance-none text-sm text-[#0F172A] font-medium pr-10 focus:outline-none transition-subtle ${
                      userType === 'student'
                        ? 'border-[#D1D5DB] focus:border-[#1B2A4A] focus:ring-1 focus:ring-[#1B2A4A]'
                        : 'border-[#E2E8F0] bg-slate-50 text-muted opacity-60 cursor-not-allowed'
                    }`}
                  >
                    {GRAD_YEARS.map((yr) => (
                      <option key={yr} value={yr}>
                        {yr}
                      </option>
                    ))}
                  </select>
                  <ChevronDown
                    size={16}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#64748B] pointer-events-none"
                  />
                </div>
                <p className="text-xs text-muted mt-1.5">
                  Helps us filter opportunities based on eligibility criteria.
                </p>
              </div>
            </div>

            {/* Row 2: "I’m looking for" & "Preferred work location" */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Field: I'm looking for */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#334155] mb-2.5">
                  I’m looking for
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* Option 1: Internships */}
                  <button
                    type="button"
                    onClick={() => setOpportunityType('internship')}
                    className={`relative p-3.5 sm:p-4 rounded-xl border text-left flex flex-col justify-between transition-all duration-200 focus:outline-none ${
                      opportunityType === 'internship'
                        ? 'border-[#1B2A4A] bg-[#F4F7FB] shadow-sm ring-1 ring-[#1B2A4A]'
                        : 'border-[#E2E8F0] bg-white hover:border-[#CBD5E1] hover:bg-slate-50/50'
                    }`}
                  >
                    <div className="flex items-start justify-between w-full mb-3">
                      <div
                        className={`w-9 h-9 rounded-lg flex items-center justify-center transition-colors ${
                          opportunityType === 'internship'
                            ? 'bg-[#1B2A4A] text-white'
                            : 'bg-[#F1F5F9] text-[#475569]'
                        }`}
                      >
                        <FileText size={18} strokeWidth={2.2} />
                      </div>
                      <div
                        className={`w-4 h-4 rounded-full border flex items-center justify-center transition-all ${
                          opportunityType === 'internship'
                            ? 'border-[#1B2A4A] bg-[#1B2A4A]'
                            : 'border-[#CBD5E1] bg-white'
                        }`}
                      >
                        {opportunityType === 'internship' && (
                          <div className="w-1.5 h-1.5 rounded-full bg-white" />
                        )}
                      </div>
                    </div>
                    <div>
                      <span className="block text-sm font-semibold text-[#0F172A]">
                        Internships
                      </span>
                      <span className="block text-[11px] text-[#64748B] mt-0.5 leading-snug">
                        Short-term, learning opportunities
                      </span>
                    </div>
                  </button>

                  {/* Option 2: Full-time Jobs */}
                  <button
                    type="button"
                    onClick={() => setOpportunityType('full_time')}
                    className={`relative p-3.5 sm:p-4 rounded-xl border text-left flex flex-col justify-between transition-all duration-200 focus:outline-none ${
                      opportunityType === 'full_time'
                        ? 'border-[#1B2A4A] bg-[#F4F7FB] shadow-sm ring-1 ring-[#1B2A4A]'
                        : 'border-[#E2E8F0] bg-white hover:border-[#CBD5E1] hover:bg-slate-50/50'
                    }`}
                  >
                    <div className="flex items-start justify-between w-full mb-3">
                      <div
                        className={`w-9 h-9 rounded-lg flex items-center justify-center transition-colors ${
                          opportunityType === 'full_time'
                            ? 'bg-[#1B2A4A] text-white'
                            : 'bg-[#F1F5F9] text-[#475569]'
                        }`}
                      >
                        <Building2 size={18} strokeWidth={2.2} />
                      </div>
                      <div
                        className={`w-4 h-4 rounded-full border flex items-center justify-center transition-all ${
                          opportunityType === 'full_time'
                            ? 'border-[#1B2A4A] bg-[#1B2A4A]'
                            : 'border-[#CBD5E1] bg-white'
                        }`}
                      >
                        {opportunityType === 'full_time' && (
                          <div className="w-1.5 h-1.5 rounded-full bg-white" />
                        )}
                      </div>
                    </div>
                    <div>
                      <span className="block text-sm font-semibold text-[#0F172A]">
                        Full-time Jobs
                      </span>
                      <span className="block text-[11px] text-[#64748B] mt-0.5 leading-snug">
                        Long-term career opportunities
                      </span>
                    </div>
                  </button>
                </div>
              </div>

              {/* Field: Preferred work location */}
              <div>
                <label
                  htmlFor="location-select"
                  className="block text-xs font-semibold uppercase tracking-wider text-[#334155] mb-2.5"
                >
                  Preferred work location
                </label>
                <div className="relative">
                  <select
                    id="location-select"
                    value={preferredLocation}
                    onChange={(e) => setPreferredLocation(e.target.value)}
                    className="w-full h-[52px] px-4 py-2.5 bg-white border border-[#D1D5DB] rounded-xl appearance-none text-sm text-[#0F172A] font-medium pr-10 focus:outline-none focus:border-[#1B2A4A] focus:ring-1 focus:ring-[#1B2A4A] transition-subtle"
                  >
                    <option value="Remote">Remote</option>
                    <option value="On-site">On-site</option>
                    <option value="Hybrid">Hybrid</option>
                    <option value="San Francisco, CA">San Francisco, CA</option>
                    <option value="New York, NY">New York, NY</option>
                    <option value="Seattle, WA">Seattle, WA</option>
                    <option value="Austin, TX">Austin, TX</option>
                    <option value="Bangalore, India">Bangalore, India</option>
                    <option value="London, UK">London, UK</option>
                    {customLocationInput && !LOCATION_OPTIONS.includes(customLocationInput) && (
                      <option value={customLocationInput}>{customLocationInput}</option>
                    )}
                  </select>
                  <ChevronDown
                    size={16}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#64748B] pointer-events-none"
                  />
                </div>

                {/* Quick select pills */}
                <div className="flex items-center gap-2 mt-2.5">
                  {LOCATION_OPTIONS.map((loc) => (
                    <button
                      key={loc}
                      type="button"
                      onClick={() => handleLocationSelect(loc)}
                      className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                        preferredLocation === loc
                          ? 'bg-[#B0C4DE] text-[#142038] font-semibold ring-1 ring-[#1B2A4A]/20'
                          : 'bg-[#F1F5F9] text-[#475569] hover:bg-[#E2E8F0]'
                      }`}
                    >
                      {loc}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Row 3: Preferred roles */}
            <div>
              <label
                htmlFor="roles-input"
                className="block text-xs font-semibold uppercase tracking-wider text-[#334155] mb-2"
              >
                Preferred roles <span className="text-[#64748B] font-normal lowercase">(optional)</span>
              </label>
              <TagInput
                id="roles-input"
                tags={preferredRoles}
                onChange={setPreferredRoles}
                placeholder="e.g. Software Engineer, Data Analyst, Product Manager"
                helperText="Add multiple roles separated by commas."
                suggestions={['Software Engineer', 'Data Analyst', 'Product Manager', 'Frontend Developer', 'Backend Engineer']}
              />
            </div>

            {/* Row 4: Any specific interests? */}
            <div>
              <label
                htmlFor="interests-input"
                className="block text-xs font-semibold uppercase tracking-wider text-[#334155] mb-2"
              >
                Any specific interests? <span className="text-[#64748B] font-normal lowercase">(optional)</span>
              </label>
              <TagInput
                id="interests-input"
                tags={interests}
                onChange={setInterests}
                placeholder="e.g. AI/ML, Web Development, Fintech, Backend, Design"
                helperText="Helps us find more relevant opportunities for you."
                suggestions={['AI/ML', 'Fintech', 'Cloud & DevOps', 'Web Development', 'Design Systems']}
              />
            </div>
          </div>

          {/* Footer Action Area */}
          <div className="mt-12 pt-6 border-t border-border/70 flex flex-col-reverse sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs text-[#64748B]">
              <ShieldCheck size={16} className="text-[#1B2A4A]" />
              <span>Your information is private and secure.</span>
            </div>

            <button
              id="onboarding-continue-btn"
              type="button"
              onClick={handleContinue}
              disabled={isSubmitting || loadingExisting}
              className="w-full sm:w-auto min-w-[170px] px-8 py-3.5 rounded-xl bg-[#294B80] hover:bg-[#1E3760] active:bg-[#152745] text-white font-medium text-sm flex items-center justify-center gap-2.5 shadow-sm hover:shadow transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-[#1B2A4A] focus:ring-offset-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <span>Continue</span>
                  <ArrowRight size={16} strokeWidth={2.2} />
                </>
              )}
            </button>
          </div>
        </main>
      </div>
    </div>
  );
}

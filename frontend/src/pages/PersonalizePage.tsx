import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  Lock,
  Loader2,
  Target,
  FileText,
  Bell,
  Calendar,
  AlertCircle,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/lib/api';
import OnboardingHeader from '@/components/OnboardingHeader';
import OnboardingStepper from '@/components/OnboardingStepper';
import personalizeIllustration from '@/assets/personalize-illustration.png';

// ---------------------------------------------------------------------------
// Custom Icons (Pixel-matched with Reference Image 2)
// ---------------------------------------------------------------------------

function TargetOpportunityIcon() {
  return (
    <div className="w-8 h-8 rounded-lg bg-[#F0F5FA] flex items-center justify-center shrink-0 text-[#2B62C6]">
      <Target size={18} strokeWidth={2} />
    </div>
  );
}

function TailorDocIcon() {
  return (
    <div className="w-8 h-8 rounded-lg bg-[#F0F5FA] flex items-center justify-center shrink-0 text-[#2B62C6]">
      <FileText size={18} strokeWidth={2} />
    </div>
  );
}

function BellReminderIcon() {
  return (
    <div className="w-8 h-8 rounded-lg bg-[#F0F5FA] flex items-center justify-center shrink-0 text-[#2B62C6]">
      <Bell size={18} strokeWidth={2} />
    </div>
  );
}

function CalendarDigestIcon() {
  return (
    <div className="w-8 h-8 rounded-lg bg-[#F0F5FA] flex items-center justify-center shrink-0 text-[#2B62C6]">
      <Calendar size={18} strokeWidth={2} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Options Definitions
// ---------------------------------------------------------------------------

interface FocusOption {
  id: string;
  title: string;
  desc: string;
  Icon: React.ComponentType;
}

const FOCUS_OPTIONS: FocusOption[] = [
  {
    id: 'opportunities',
    title: 'Find the right opportunities',
    desc: 'Get better matches based on your profile.',
    Icon: TargetOpportunityIcon,
  },
  {
    id: 'resume',
    title: 'Tailor my resume',
    desc: 'Auto-customize for each application.',
    Icon: TailorDocIcon,
  },
  {
    id: 'deadlines',
    title: 'Never miss deadlines',
    desc: 'Reminders, follow-ups and next steps.',
    Icon: BellReminderIcon,
  },
];

interface UpdateFrequencyOption {
  id: string;
  title: string;
  desc: string;
  Icon: React.ComponentType;
}

const FREQUENCY_OPTIONS: UpdateFrequencyOption[] = [
  {
    id: 'daily',
    title: 'Daily',
    desc: 'New matches, important alerts, and progress updates.',
    Icon: CalendarDigestIcon,
  },
  {
    id: 'important',
    title: 'Only important alerts',
    desc: 'Just critical updates (like deadlines, interview invites).',
    Icon: BellReminderIcon,
  },
  {
    id: 'weekly',
    title: 'Weekly digest',
    desc: 'A short summary every week.',
    Icon: TailorDocIcon,
  },
];

const CHECKLIST_ITEMS = [
  'Personalized job matches',
  'Resume suggestions',
  'Timely alerts & reminders',
  'Insights to improve over time',
];

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------

interface PersonalizationData {
  focus_opportunity_matching: boolean;
  focus_resume_tailoring: boolean;
  focus_deadline_tracking: boolean;
  update_frequency: string;
  additional_notes: string | null;
  onboarding_step: number;
  onboarding_completed: boolean;
}

export default function PersonalizePage() {
  const navigate = useNavigate();
  const { updateOnboardingProgress } = useAuth();

  // Multi-select for Focus Areas (default: opportunities checked)
  const [selectedFocus, setSelectedFocus] = useState<string[]>(['opportunities']);

  // Single-select for Update Frequency (default: 'daily')
  const [selectedFrequency, setSelectedFrequency] = useState<string>('daily');

  // Optional Note Textarea
  const [additionalNotes, setAdditionalNotes] = useState<string>('');

  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Restore saved selections on mount
  useEffect(() => {
    let isMounted = true;
    api
      .get<PersonalizationData>('/api/v1/onboarding/personalization')
      .then((data) => {
        if (!isMounted || !data) return;

        const focus: string[] = [];
        if (data.focus_opportunity_matching) focus.push('opportunities');
        if (data.focus_resume_tailoring) focus.push('resume');
        if (data.focus_deadline_tracking) focus.push('deadlines');

        if (focus.length > 0) {
          setSelectedFocus(focus);
        }

        if (data.update_frequency) {
          const freq =
            data.update_frequency === 'important_only' ? 'important' : data.update_frequency;
          setSelectedFrequency(freq);
        }

        if (data.additional_notes) {
          setAdditionalNotes(data.additional_notes);
        }
      })
      .catch((err) => {
        console.error('Failed to load personalization preferences:', err);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const toggleFocus = (id: string) => {
    setErrorMessage(null);
    if (selectedFocus.includes(id)) {
      setSelectedFocus(selectedFocus.filter((item) => item !== id));
    } else {
      setSelectedFocus([...selectedFocus, id]);
    }
  };

  const handleContinue = async () => {
    // 1. Validate required selections
    if (selectedFocus.length === 0) {
      setErrorMessage('Please select at least one focus area to personalize your copilot.');
      return;
    }
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      // 2. Save personalization preferences
      const payload = {
        focus_opportunity_matching: selectedFocus.includes('opportunities'),
        focus_resume_tailoring: selectedFocus.includes('resume'),
        focus_deadline_tracking: selectedFocus.includes('deadlines'),
        update_frequency: selectedFrequency === 'important' ? 'important_only' : selectedFrequency,
        additional_notes: additionalNotes.trim() || null,
      };

      await api.put<PersonalizationData>('/api/v1/onboarding/personalization', payload);

      // 3. Set onboarding_step = 4
      await updateOnboardingProgress(4);

      // 4. Animate current page out LEFT
      setIsTransitioning(true);

      // 5. Navigate to /onboarding/complete
      setTimeout(() => {
        navigate('/onboarding/complete');
      }, 300);
    } catch (err: unknown) {
      setIsSubmitting(false);
      const msg = err instanceof Error ? err.message : 'Unable to save preferences. Please try again.';
      setErrorMessage(msg);
    }
  };

  const handleBack = () => {
    navigate('/onboarding/resume');
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col font-inter text-[#1A1A1A] selection:bg-[#2B62C6]/15">
      {/* Header */}
      <OnboardingHeader />

      {/* Main Content Area */}
      <main
        className={`flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 flex flex-col ${
          isTransitioning ? 'animate-slide-left-out' : 'animate-slide-up'
        }`}
      >
        {/* Stepper (Step 1=Completed, Step 2=Completed, Step 3=Active, Step 4=Upcoming) */}
        <div className="mb-8 sm:mb-10">
          <OnboardingStepper currentStep={3} />
        </div>

        {/* Error Message Alert */}
        {errorMessage && (
          <div className="mb-4 p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-start gap-2.5 animate-fade-in max-w-3xl">
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

        {/* 2-Column Main Section (Desktop: Two Columns, Mobile: Stacked) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start">
          {/* ============================================================== */}
          {/* LEFT COLUMN: Personalization Form                             */}
          {/* ============================================================== */}
          <div className="lg:col-span-7 xl:col-span-8 flex flex-col">
            {/* Main Heading & Subtext */}
            <div className="mb-6 sm:mb-7">
              <h1 className="font-serif text-[28px] sm:text-[32px] lg:text-[34px] font-bold text-[#111827] tracking-tight leading-tight">
                Personalize your AI copilot.
              </h1>
              <p className="text-[13.5px] sm:text-[14px] text-[#64748B] mt-1.5 font-normal leading-relaxed">
                Tell us how you want to use Aptly. We’ll tailor recommendations and help you get the most out of it.
              </p>
            </div>

            {/* ------------------------------------------------------------ */}
            {/* SECTION 1: What would you like to focus on? (Multi-select)   */}
            {/* ------------------------------------------------------------ */}
            <div className="mb-6 sm:mb-7">
              <h2 className="text-[14px] sm:text-[14.5px] font-bold text-[#111827] leading-snug">
                What would you like to focus on?
              </h2>
              <p className="text-[12px] text-[#64748B] mt-0.5 mb-3">
                Choose one or more options.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {FOCUS_OPTIONS.map((opt) => {
                  const isChecked = selectedFocus.includes(opt.id);
                  const { Icon } = opt;

                  return (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => toggleFocus(opt.id)}
                      className={`p-4 rounded-xl border text-left flex flex-col justify-between transition-all duration-200 cursor-pointer relative ${
                        isChecked
                          ? 'border-[#2B62C6] bg-[#F0F6FD] shadow-xs'
                          : 'border-[#E2E8F0] bg-white hover:border-[#CBD5E1] hover:bg-[#F8FAFC]'
                      }`}
                      style={{ minHeight: '130px' }}
                    >
                      {/* Top row: Icon + Checkbox */}
                      <div className="flex items-start justify-between w-full mb-3">
                        <Icon />

                        {/* Checkbox box */}
                        <div
                          className={`w-4.5 h-4.5 rounded-md border flex items-center justify-center transition-all ${
                            isChecked
                              ? 'border-[#2B62C6] bg-[#2B62C6] text-white'
                              : 'border-[#CBD5E1] bg-white'
                          }`}
                        >
                          {isChecked && <Check size={12} strokeWidth={3} />}
                        </div>
                      </div>

                      {/* Text content */}
                      <div>
                        <p className="text-[13px] font-bold text-[#111827] leading-snug">
                          {opt.title}
                        </p>
                        <p className="text-[11.5px] text-[#64748B] mt-1 leading-snug">
                          {opt.desc}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* ------------------------------------------------------------ */}
            {/* SECTION 2: How often should I keep you updated? (Single-sel) */}
            {/* ------------------------------------------------------------ */}
            <div className="mb-6 sm:mb-7">
              <h2 className="text-[14px] sm:text-[14.5px] font-bold text-[#111827] leading-snug">
                How often should I keep you updated?
              </h2>
              <p className="text-[12px] text-[#64748B] mt-0.5 mb-3">
                Choose one option.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {FREQUENCY_OPTIONS.map((opt) => {
                  const isSelected = selectedFrequency === opt.id;
                  const { Icon } = opt;

                  return (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setSelectedFrequency(opt.id)}
                      className={`p-4 rounded-xl border text-left flex flex-col justify-between transition-all duration-200 cursor-pointer relative ${
                        isSelected
                          ? 'border-[#2B62C6] bg-[#F0F6FD] shadow-xs'
                          : 'border-[#E2E8F0] bg-white hover:border-[#CBD5E1] hover:bg-[#F8FAFC]'
                      }`}
                      style={{ minHeight: '130px' }}
                    >
                      {/* Top row: Icon + Radio button */}
                      <div className="flex items-start justify-between w-full mb-3">
                        <Icon />

                        {/* Radio circle */}
                        <div
                          className={`w-4.5 h-4.5 rounded-full border flex items-center justify-center transition-all ${
                            isSelected
                              ? 'border-[#2B62C6] bg-white ring-1 ring-[#2B62C6]'
                              : 'border-[#CBD5E1] bg-white'
                          }`}
                        >
                          {isSelected && <div className="w-2.5 h-2.5 rounded-full bg-[#2B62C6]" />}
                        </div>
                      </div>

                      {/* Text content */}
                      <div>
                        <p className="text-[13px] font-bold text-[#111827] leading-snug">
                          {opt.title}
                        </p>
                        <p className="text-[11.5px] text-[#64748B] mt-1 leading-snug">
                          {opt.desc}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* ------------------------------------------------------------ */}
            {/* SECTION 3: Anything else I should know? (Optional Textarea) */}
            {/* ------------------------------------------------------------ */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label
                  htmlFor="personalize-notes"
                  className="block text-[14px] sm:text-[14.5px] font-bold text-[#111827]"
                >
                  Anything else I should know?{' '}
                  <span className="text-[#64748B] font-normal text-[13px]">(optional)</span>
                </label>
              </div>

              <div className="relative">
                <textarea
                  id="personalize-notes"
                  rows={3}
                  maxLength={300}
                  placeholder="e.g. I prefer startups, don’t want unpaid internships, open to relocation, interested in research roles, etc."
                  value={additionalNotes}
                  onChange={(e) => setAdditionalNotes(e.target.value)}
                  className="w-full p-3.5 rounded-xl border border-[#E2E8F0] bg-white text-[13px] text-[#1A1A1A] placeholder:text-[#94A3B8] focus:outline-none focus:ring-1 focus:ring-[#2B62C6] focus:border-[#2B62C6] transition-colors resize-none leading-relaxed"
                />
                <div className="text-right text-[11.5px] text-[#94A3B8] mt-1 pr-1 font-medium">
                  {additionalNotes.length}/300
                </div>
              </div>
            </div>
          </div>

          {/* ============================================================== */}
          {/* RIGHT COLUMN: Illustration & Assistant Info Panel             */}
          {/* ============================================================== */}
          <div className="lg:col-span-5 xl:col-span-4 flex flex-col">
            <div className="w-full bg-white rounded-2xl border border-[#E2E8F0] overflow-hidden shadow-xs p-6">
              {/* IMAGE 1: AI Personalization Illustration Asset */}
              <div className="w-full flex items-center justify-center pointer-events-none select-none mb-4">
                <img
                  src={personalizeIllustration}
                  alt="AI copilot learning illustration"
                  className="w-full max-w-[280px] h-auto object-contain max-h-[190px]"
                  draggable={false}
                />
              </div>

              {/* Title & Description */}
              <h3 className="text-[15px] font-bold text-[#111827] mb-1.5">
                Your copilot is learning
              </h3>
              <p className="text-[12.5px] text-[#64748B] leading-relaxed mb-4">
                I’ll use your preferences and resume to find the most relevant opportunities, tailor your applications, and keep you on track.
              </p>

              {/* Checklist */}
              <div className="space-y-2.5 mb-5">
                {CHECKLIST_ITEMS.map((item) => (
                  <div key={item} className="flex items-center gap-2 text-[12.5px] text-[#334155]">
                    <CheckCircle2 size={16} className="text-[#2B62C6] shrink-0" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>

              {/* Bottom Privacy Box */}
              <div className="rounded-xl bg-[#F0F6FD] p-3.5 flex items-center gap-3 border border-[#E2E8F0]/60">
                <Lock size={16} className="text-[#2B62C6] shrink-0" />
                <span className="text-[12px] text-[#24416B] font-medium leading-snug">
                  Your information stays private and secure.
                </span>
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

          {/* Continue button */}
          <button
            id="personalize-continue-btn"
            type="button"
            onClick={handleContinue}
            disabled={isSubmitting || isLoading}
            className="min-w-[140px] px-7 py-2.5 rounded-xl bg-[#234C8E] hover:bg-[#1C3E75] active:bg-[#16305C] text-white font-medium text-[13.5px] flex items-center justify-center gap-2 shadow-sm hover:shadow transition-all duration-200 cursor-pointer disabled:opacity-60"
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

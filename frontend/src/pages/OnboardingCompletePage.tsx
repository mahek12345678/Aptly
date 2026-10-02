import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, ArrowRight, LayoutDashboard, Loader2, FileText, SlidersHorizontal, Bot } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import OnboardingHeader from '@/components/OnboardingHeader';
import OnboardingStepper from '@/components/OnboardingStepper';

export default function OnboardingCompletePage() {
  const navigate = useNavigate();
  const { updateOnboardingProgress } = useAuth();
  const [isFinishing, setIsFinishing] = useState(false);

  const handleFinish = async () => {
    setIsFinishing(true);
    try {
      // Mark onboarding as complete on backend and in state (keeps step 4)
      await updateOnboardingProgress(4, true);
      navigate('/dashboard', { replace: true });
    } catch {
      navigate('/dashboard', { replace: true });
    } finally {
      setIsFinishing(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col font-inter text-[#1A1A1A]">
      <OnboardingHeader />

      <main className="flex-1 w-full max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-12 flex flex-col justify-center animate-slide-up">
        {/* Stepper */}
        <div className="mb-8 sm:mb-10">
          <OnboardingStepper currentStep={4} />
        </div>

        {/* Celebratory Container */}
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-7 sm:p-10 shadow-xs text-center">
          {/* Badge */}
          <div className="w-16 h-16 rounded-2xl bg-[#EBF3FC] text-[#2B62C6] flex items-center justify-center mx-auto mb-4 shadow-xs">
            <CheckCircle2 size={30} strokeWidth={2.2} />
          </div>

          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-xs font-semibold text-emerald-700 border border-emerald-100 mb-3">
            <CheckCircle2 size={13} />
            <span>Setup Complete</span>
          </span>

          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#111827] font-serif leading-tight mb-2.5">
            You&apos;re all set.
          </h1>

          <p className="text-[14px] sm:text-[14.5px] text-[#64748B] max-w-md mx-auto leading-relaxed mb-7">
            Aptly is ready to help you find, tailor, and track the right opportunities.
          </p>

          {/* Compact Summary Component */}
          <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-4 sm:p-5 max-w-md mx-auto mb-8 text-left divide-y divide-[#E2E8F0]/70">
            <div className="flex items-center justify-between py-2.5 first:pt-1">
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-lg bg-white border border-[#E2E8F0] flex items-center justify-center text-[#2B62C6]">
                  <FileText size={15} />
                </div>
                <span className="text-[13px] font-medium text-[#334155]">Resume</span>
              </div>
              <span className="inline-flex items-center gap-1 text-[12px] font-semibold text-emerald-600 bg-emerald-50 border border-emerald-100 px-2.5 py-0.5 rounded-full">
                <CheckCircle2 size={12} />
                Ready
              </span>
            </div>

            <div className="flex items-center justify-between py-2.5">
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-lg bg-white border border-[#E2E8F0] flex items-center justify-center text-[#2B62C6]">
                  <SlidersHorizontal size={15} />
                </div>
                <span className="text-[13px] font-medium text-[#334155]">Preferences</span>
              </div>
              <span className="inline-flex items-center gap-1 text-[12px] font-semibold text-emerald-600 bg-emerald-50 border border-emerald-100 px-2.5 py-0.5 rounded-full">
                <CheckCircle2 size={12} />
                Saved
              </span>
            </div>

            <div className="flex items-center justify-between py-2.5 last:pb-1">
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-lg bg-white border border-[#E2E8F0] flex items-center justify-center text-[#2B62C6]">
                  <Bot size={15} />
                </div>
                <span className="text-[13px] font-medium text-[#334155]">AI profile</span>
              </div>
              <span className="inline-flex items-center gap-1 text-[12px] font-semibold text-emerald-600 bg-emerald-50 border border-emerald-100 px-2.5 py-0.5 rounded-full">
                <CheckCircle2 size={12} />
                Personalized
              </span>
            </div>
          </div>

          {/* Primary CTA Button */}
          <button
            id="go-to-dashboard-btn"
            type="button"
            onClick={handleFinish}
            disabled={isFinishing}
            className="w-full sm:w-auto min-w-[220px] px-8 py-3 rounded-xl bg-[#234C8E] hover:bg-[#1C3E75] active:bg-[#16305C] text-white font-medium text-[14px] inline-flex items-center justify-center gap-2.5 shadow-sm hover:shadow transition-all duration-200 cursor-pointer disabled:opacity-50"
          >
            {isFinishing ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Launching Dashboard…</span>
              </>
            ) : (
              <>
                <LayoutDashboard size={16} />
                <span>Go to dashboard</span>
                <ArrowRight size={16} strokeWidth={2.2} />
              </>
            )}
          </button>
        </div>
      </main>
    </div>
  );
}

import React, { useEffect, useState, useCallback } from 'react';
import { Mail, CheckCircle2 } from 'lucide-react';
import { api } from '@/lib/api';
import { JobApplication } from '@/types/application';

interface ActiveIntent {
  id: string;
  company: string;
  role: string;
  startedAt: number;
}

export const DashboardApplicationIntentBanner: React.FC = () => {
  const [activePrompt, setActivePrompt] = useState<ActiveIntent | null>(null);
  const [statusFeedback, setStatusFeedback] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Check if there is an active pending application intent
  const checkPendingIntent = useCallback(() => {
    try {
      const stored = sessionStorage.getItem('aptly_active_apply_intent');
      if (!stored) {
        setActivePrompt(null);
        return;
      }

      const intent: ActiveIntent = JSON.parse(stored);
      const dismissed = sessionStorage.getItem(`aptly_intent_dismissed_${intent.id}`);
      if (dismissed) {
        setActivePrompt(null);
        return;
      }

      // Check minimum delay to avoid immediate flicker
      const elapsed = Date.now() - intent.startedAt;
      if (elapsed < 1200) return;

      setActivePrompt(intent);
    } catch (e) {
      console.error('Failed to parse active apply intent:', e);
      setActivePrompt(null);
    }
  }, []);

  useEffect(() => {
    const handleApplyStarted = () => {
      setTimeout(() => {
        checkPendingIntent();
      }, 1500);
    };

    const handleFocus = () => {
      checkPendingIntent();
    };

    window.addEventListener('aptly:apply-started', handleApplyStarted);
    window.addEventListener('focus', handleFocus);
    document.addEventListener('visibilitychange', handleFocus);

    checkPendingIntent();

    return () => {
      window.removeEventListener('aptly:apply-started', handleApplyStarted);
      window.removeEventListener('focus', handleFocus);
      document.removeEventListener('visibilitychange', handleFocus);
    };
  }, [checkPendingIntent]);

  const handleConfirmApplied = async () => {
    if (!activePrompt || isSubmitting) return;
    setIsSubmitting(true);

    try {
      await api.post<JobApplication>(
        `/api/v1/applications/${activePrompt.id}/confirm-applied`
      );

      setStatusFeedback('Application recorded in ledger');
      sessionStorage.setItem(`aptly_intent_dismissed_${activePrompt.id}`, 'true');
      sessionStorage.removeItem('aptly_active_apply_intent');

      // Dispatch event to refresh dashboard & kanban
      window.dispatchEvent(
        new CustomEvent('aptly:application-confirmed', {
          detail: { id: activePrompt.id },
        })
      );

      setTimeout(() => {
        setActivePrompt(null);
        setStatusFeedback(null);
        setIsSubmitting(false);
      }, 1800);
    } catch (err) {
      console.error('Failed to confirm applied:', err);
      setIsSubmitting(false);
    }
  };

  const handleNotYet = async () => {
    if (!activePrompt || isSubmitting) return;
    setIsSubmitting(true);

    try {
      await api.post<JobApplication>(
        `/api/v1/applications/${activePrompt.id}/not-yet`
      );
    } catch (err) {
      console.error('Failed to mark not-yet:', err);
    } finally {
      sessionStorage.setItem(`aptly_intent_dismissed_${activePrompt.id}`, 'true');
      sessionStorage.removeItem('aptly_active_apply_intent');
      setActivePrompt(null);
      setIsSubmitting(false);
    }
  };

  if (!activePrompt && !statusFeedback) return null;

  return (
    <div className="rounded-lg border border-[#E2E2E2] bg-white p-3.5 sm:px-5 sm:py-3.5 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-fade-in">
      {statusFeedback ? (
        <div className="flex items-center gap-2.5 text-[#1B2A4A] text-[13px] font-medium py-1">
          <CheckCircle2 size={16} className="text-[#1E4D3A] shrink-0" />
          <span>{statusFeedback}</span>
        </div>
      ) : (
        <>
          <div className="flex items-center gap-3 min-w-0">
            <span className="w-8 h-8 rounded border border-[#E2E2E2] bg-[#FAFAFA] flex items-center justify-center text-[#1B2A4A] shrink-0">
              <Mail size={15} />
            </span>
            <p className="text-[13.5px] text-[#1A1A1A] leading-snug truncate">
              Did you finish applying to{' '}
              <span className="font-semibold text-[#1A1A1A]">
                {activePrompt?.company} — {activePrompt?.role}
              </span>
              ?
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
            <button
              type="button"
              disabled={isSubmitting}
              onClick={handleConfirmApplied}
              className="px-3.5 py-1.5 rounded bg-[#1B2A4A] hover:bg-[#233860] active:scale-[0.98] text-white text-[12.5px] font-medium transition-colors cursor-pointer disabled:opacity-50"
            >
              Yes, I applied
            </button>
            <button
              type="button"
              disabled={isSubmitting}
              onClick={handleNotYet}
              className="px-3 py-1.5 rounded border border-[#E2E2E2] bg-white hover:bg-[#F9FAFB] active:scale-[0.98] text-[#1A1A1A] text-[12.5px] font-medium transition-colors cursor-pointer disabled:opacity-50"
            >
              Not yet
            </button>
          </div>
        </>
      )}
    </div>
  );
};

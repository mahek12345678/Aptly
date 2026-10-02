import React, { useEffect, useState, useCallback } from 'react';
import { CheckCircle2, Clock, X, ArrowRight } from 'lucide-react';
import { api } from '@/lib/api';
import { JobApplication } from '@/types/application';

interface ActiveIntent {
  id: string;
  company: string;
  role: string;
  startedAt: number;
}

export const ApplicationIntentBanner: React.FC = () => {
  const [activePrompt, setActivePrompt] = useState<ActiveIntent | null>(null);
  const [statusFeedback, setStatusFeedback] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Check if we should prompt the user
  const checkPendingIntent = useCallback(() => {
    try {
      const stored = sessionStorage.getItem('aptly_active_apply_intent');
      if (!stored) return;

      const intent: ActiveIntent = JSON.parse(stored);
      // Check if already dismissed or responded
      const dismissed = sessionStorage.getItem(`aptly_intent_dismissed_${intent.id}`);
      if (dismissed) return;

      // Don't prompt immediately while still clicking; wait at least 1.5 seconds since started
      const elapsed = Date.now() - intent.startedAt;
      if (elapsed < 1500) return;

      setActivePrompt(intent);
    } catch (e) {
      console.error('Failed to parse active apply intent:', e);
    }
  }, []);

  useEffect(() => {
    // Listen to custom start events
    const handleApplyStarted = (event: Event) => {
      const customEvent = event as CustomEvent<ActiveIntent>;
      if (customEvent.detail) {
        // Will show when user switches tab or after delay
        setTimeout(() => {
          checkPendingIntent();
        }, 1500);
      }
    };

    // Listen to window focus (when user returns from external job page)
    const handleFocus = () => {
      checkPendingIntent();
    };

    window.addEventListener('aptly:apply-started', handleApplyStarted);
    window.addEventListener('focus', handleFocus);
    document.addEventListener('visibilitychange', handleFocus);

    // Initial check on mount
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

      setStatusFeedback('Added to Track Jobs');
      sessionStorage.setItem(`aptly_intent_dismissed_${activePrompt.id}`, 'true');
      sessionStorage.removeItem('aptly_active_apply_intent');

      // Notify other parts of the app (e.g. Kanban or Dashboard)
      window.dispatchEvent(
        new CustomEvent('aptly:application-confirmed', {
          detail: { id: activePrompt.id },
        })
      );

      setTimeout(() => {
        setActivePrompt(null);
        setStatusFeedback(null);
        setIsSubmitting(false);
      }, 2000);
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
    <div className="fixed bottom-5 right-5 sm:bottom-6 sm:right-6 z-50 max-w-sm sm:max-w-md w-[calc(100vw-2.5rem)] animate-in slide-in-from-bottom-5 fade-in duration-200">
      <div className="p-4 sm:p-4.5 rounded-2xl bg-[#1B2A4A] text-white shadow-xl border border-white/10 flex flex-col gap-3">
        {statusFeedback ? (
          <div className="flex items-center gap-2.5 text-emerald-300 font-semibold text-xs sm:text-sm py-1">
            <CheckCircle2 size={18} className="text-emerald-400 shrink-0" />
            <span>{statusFeedback}</span>
          </div>
        ) : (
          <>
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-2.5">
                <span className="p-1.5 rounded-lg bg-white/10 text-blue-300 mt-0.5">
                  <Clock size={16} />
                </span>
                <div>
                  <h4 className="font-serif text-sm sm:text-[14.5px] font-bold text-white leading-snug">
                    Did you apply to {activePrompt?.company}?
                  </h4>
                  <p className="text-xs text-slate-300 mt-0.5 font-medium line-clamp-1">
                    {activePrompt?.role}
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={handleNotYet}
                aria-label="Dismiss banner"
                className="text-slate-400 hover:text-white p-1 rounded transition-colors cursor-pointer"
              >
                <X size={15} />
              </button>
            </div>

            <div className="flex items-center justify-end gap-2 pt-1 border-t border-white/10">
              <button
                type="button"
                disabled={isSubmitting}
                onClick={handleNotYet}
                className="px-3 py-1.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
              >
                Not yet
              </button>

              <button
                type="button"
                disabled={isSubmitting}
                onClick={handleConfirmApplied}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-white hover:bg-slate-100 text-[#1B2A4A] text-xs font-bold transition-all shadow-xs cursor-pointer active:scale-95"
              >
                <span>Yes, I applied</span>
                <ArrowRight size={13} />
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

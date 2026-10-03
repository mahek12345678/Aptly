import { api } from '@/lib/api';
import { ApplicationStartPayload, JobApplication } from '@/types/application';

export async function startApplicationIntent(
  payload: ApplicationStartPayload
): Promise<JobApplication> {
  const application = await api.post<JobApplication>(
    '/api/v1/applications/start',
    payload
  );

  // Store in sessionStorage for confirmation banner upon return
  const activeIntent = {
    id: application.id,
    company: application.company,
    role: application.role,
    startedAt: Date.now(),
  };
  sessionStorage.setItem('aptly_active_apply_intent', JSON.stringify(activeIntent));

  // Open external application page in new tab
  if (payload.application_url) {
    window.open(payload.application_url, '_blank', 'noopener,noreferrer');
  }

  // Notify active listeners
  window.dispatchEvent(
    new CustomEvent('aptly:apply-started', {
      detail: activeIntent,
    })
  );

  return application;
}

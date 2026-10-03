import type { UserProfile } from '@/contexts/AuthContext';

export function getOnboardingRouteForStep(step: number): string {
  switch (step) {
    case 1:
      return '/onboarding';
    case 2:
      return '/onboarding/resume';
    case 3:
      return '/onboarding/personalize';
    case 4:
      return '/onboarding/complete';
    default:
      return '/onboarding';
  }
}

export function getTargetRouteForUser(user: UserProfile | null): string {
  if (!user) return '/login';
  if (user.onboarding_completed) return '/dashboard';
  return getOnboardingRouteForStep(user.onboarding_step || 1);
}

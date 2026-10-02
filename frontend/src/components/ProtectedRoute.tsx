import { type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { getTargetRouteForUser } from '@/lib/auth-helpers';

interface ProtectedRouteProps {
  children: ReactNode;
}

/**
 * Wraps a route and redirects to /login if the user is not authenticated.
 * Preserves the intended destination so we can redirect back after login.
 * Also enforces the onboarding gate:
 * - If user has not completed onboarding and tries to access app pages, redirect to current onboarding step.
 * - If user has completed onboarding and tries to access /onboarding, redirect to /dashboard.
 */
export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="w-5 h-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  const isOnboardingRoute = location.pathname.startsWith('/onboarding');

  // If user has NOT completed onboarding, prevent access to protected app routes
  if (!user.onboarding_completed && !isOnboardingRoute) {
    return <Navigate to={getTargetRouteForUser(user)} replace />;
  }

  // If user HAS completed onboarding, prevent them from landing back in onboarding
  if (user.onboarding_completed && isOnboardingRoute) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}

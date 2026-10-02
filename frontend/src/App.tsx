import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import { AssistantProvider } from '@/contexts/AssistantContext';
import ProtectedRoute from '@/components/ProtectedRoute';
import LoginPage from '@/pages/LoginPage';
import SignupPage from '@/pages/SignupPage';
import OnboardingPage from '@/pages/OnboardingPage';
import ResumePlaceholderPage from '@/pages/ResumePlaceholderPage';
import PersonalizePage from '@/pages/PersonalizePage';
import OnboardingCompletePage from '@/pages/OnboardingCompletePage';
import DashboardPage from '@/pages/DashboardPage';
import TrackJobsPage from '@/pages/TrackJobsPage';
import FindPositionsPage from '@/pages/FindPositionsPage';
import JDAnalyzerPage from '@/pages/JDAnalyzerPage';
import AboutPage from '@/pages/AboutPage';
import ProfilePage from '@/pages/ProfilePage';
import { getTargetRouteForUser } from '@/lib/auth-helpers';

const queryClient = new QueryClient();

/** Redirect / -> /login or /dashboard or /onboarding depending on user auth state and onboarding progress. */
function RootRedirect() {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="w-5 h-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  return <Navigate to={getTargetRouteForUser(user)} replace />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <AuthProvider>
          <AssistantProvider>
            <Routes>
            <Route path="/" element={<RootRedirect />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route
              path="/onboarding"
              element={
                <ProtectedRoute>
                  <OnboardingPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/onboarding/resume"
              element={
                <ProtectedRoute>
                  <ResumePlaceholderPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/onboarding/personalize"
              element={
                <ProtectedRoute>
                  <PersonalizePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/onboarding/complete"
              element={
                <ProtectedRoute>
                  <OnboardingCompletePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/track-jobs"
              element={
                <ProtectedRoute>
                  <TrackJobsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/find-positions"
              element={
                <ProtectedRoute>
                  <FindPositionsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/jd-analyzer"
              element={
                <ProtectedRoute>
                  <JDAnalyzerPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/about"
              element={
                <ProtectedRoute>
                  <AboutPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <ProfilePage />
                </ProtectedRoute>
              }
            />
            {/* Catch-all */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </AssistantProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

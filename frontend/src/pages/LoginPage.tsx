import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { GoogleLogin, type CredentialResponse } from '@react-oauth/google';
import { AlertCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { getTargetRouteForUser } from '@/lib/auth-helpers';
import careerRoadImg from '@/assets/career-road.png';
import { AptlyLogo } from '@/components/common/AptlyLogo';

// ---------------------------------------------------------------------------
// Custom Feature Icons (Pixel-matched with Reference)
// ---------------------------------------------------------------------------

function SearchFeatureIcon() {
  return (
    <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-[#EBF3FC] flex items-center justify-center shrink-0 text-[#2B62C6]">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="7.5" />
        <path d="m20.5 20.5-4-4" />
      </svg>
    </div>
  );
}

function ResumeFeatureIcon() {
  return (
    <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-[#EBF3FC] flex items-center justify-center shrink-0 text-[#2B62C6]">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <path d="M14 2v6h6" />
        <path d="M16 13H8" />
        <path d="M16 17H8" />
        <path d="M10 9H8" />
      </svg>
    </div>
  );
}

function DashboardFeatureIcon() {
  return (
    <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-[#EBF3FC] flex items-center justify-center shrink-0 text-[#2B62C6]">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="18" rx="1.5" />
        <rect x="14" y="3" width="7" height="11" rx="1.5" />
      </svg>
    </div>
  );
}

function LoopFeatureIcon() {
  return (
    <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-[#EBF3FC] flex items-center justify-center shrink-0 text-[#2B62C6]">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3" />
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Feature List Definition
// ---------------------------------------------------------------------------

const featureList = [
  {
    Icon: SearchFeatureIcon,
    title: 'Find opportunities',
    description: 'Get personalized job & internship matches daily, powered by AI.',
  },
  {
    Icon: ResumeFeatureIcon,
    title: 'Tailor your resume',
    description: 'Turn any job description into a customized, high-impact resume.',
  },
  {
    Icon: DashboardFeatureIcon,
    title: 'Track your progress',
    description: 'A clear, visual dashboard for all your applications.',
  },
  {
    Icon: LoopFeatureIcon,
    title: 'Stay in the loop',
    description: 'Get AI-powered insights and voice updates, personalized for you.',
  },
];

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function LoginPage() {
  const { login, user, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();

  // If already authenticated, redirect to appropriate target route
  useEffect(() => {
    if (isAuthenticated && user) {
      navigate(getTargetRouteForUser(user), { replace: true });
    }
  }, [isAuthenticated, user, navigate]);

  // Error states
  const [googleError, setGoogleError] = useState<string | null>(null);
  const [notFoundError, setNotFoundError] = useState(false);

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    if (!credentialResponse.credential) {
      setGoogleError('Google did not return a credential. Please try again.');
      setNotFoundError(false);
      return;
    }
    setGoogleError(null);
    setNotFoundError(false);
    try {
      const loggedInUser = await login(credentialResponse.credential);
      const targetRoute = getTargetRouteForUser(loggedInUser);
      navigate(targetRoute, { replace: true });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Authentication failed.';
      if (msg.includes('No Aptly account found') || msg.includes('Create one first')) {
        setNotFoundError(true);
      } else {
        setNotFoundError(false);
        setGoogleError(msg);
      }
    }
  };

  const handleGoogleError = () => {
    setNotFoundError(false);
    setGoogleError('Google sign-in was cancelled or failed. Please try again.');
  };

  return (
    <div className="min-h-screen lg:h-screen lg:max-h-screen flex flex-col bg-[#FAFAFA] text-[#1A1A1A] font-inter selection:bg-[#2B62C6]/15 overflow-x-hidden lg:overflow-hidden">
      {/* ================================================================ */}
      {/* TOP HEADER (Compact, crisp)                                      */}
      {/* ================================================================ */}
      <header className="w-full px-6 sm:px-10 lg:px-14 xl:px-16 py-2.5 sm:py-3 flex items-center justify-between border-b border-[#E2E2E2] bg-white z-20 shrink-0">
        {/* Brand Logo */}
        <AptlyLogo height={30} variant="full" />

        {/* Header Right Tagline */}
        <p className="text-[12.5px] sm:text-[13px] text-[#6B6B6B] hidden sm:block font-normal">
          A calmer way to your next opportunity.
        </p>
      </header>

      {/* ================================================================ */}
      {/* MAIN CONTAINER (Left Section + Right Login Panel)               */}
      {/* ================================================================ */}
      <main className="flex-1 flex flex-col lg:flex-row w-full relative min-h-0">
        {/* -------------------------------------------------------------- */}
        {/* LEFT SECTION (Hero, Features, Handwritten Quote, Illustration) */}
        {/* -------------------------------------------------------------- */}
        <section className="flex-1 relative flex flex-col justify-between px-6 sm:px-10 lg:px-12 xl:px-16 py-5 sm:py-6 lg:py-6 xl:py-8 overflow-y-auto lg:overflow-hidden min-h-0 bg-[#FAFAFA]">
          <div className="max-w-lg xl:max-w-xl relative z-10">
            {/* Main Headline */}
            <h1 className="font-serif text-[34px] sm:text-[40px] lg:text-[43px] xl:text-[48px] font-bold text-[#111827] leading-[1.12] tracking-tight mb-2.5 sm:mb-3">
              Your career journey,
              <br />
              with an <span className="text-[#2B62C6]">AI copilot.</span>
            </h1>

            {/* Supporting Copy */}
            <p className="text-[13.5px] sm:text-[14px] leading-relaxed text-[#556377] mb-4 sm:mb-5 max-w-[460px]">
              From finding the right opportunities to tailoring your resume and
              tracking your applications — Aptly handles the busywork, so you
              can focus on what’s next.
            </p>

            {/* 4 Feature Rows */}
            <div className="space-y-2.5 sm:space-y-3 max-w-[460px] xl:max-w-[490px]">
              {featureList.map(({ Icon, title, description }) => (
                <div key={title} className="flex items-start gap-3">
                  <Icon />
                  <div className="pt-0.5">
                    <h2 className="text-[13.5px] sm:text-[14px] font-bold text-[#111827] leading-tight">
                      {title}
                    </h2>
                    <p className="text-[12px] sm:text-[12.5px] text-[#6B6B6B] mt-0.5 leading-snug">
                      {description}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* Handwritten Quote */}
            <div className="mt-4 sm:mt-5 mb-2 sm:mb-3">
              <div className="font-handwriting text-[20px] sm:text-[22px] text-[#475569] leading-tight select-none">
                <p>Same you.</p>
                <p>A more intentional next step.</p>
              </div>
              <div className="w-5 h-[1.5px] bg-[#64748B] mt-1.5" />
            </div>
          </div>

          {/* Bottom Left Footer Note */}
          <div className="pt-1 relative z-10">
            <p className="text-[11px] sm:text-[11.5px] text-[#6B6B6B]">
              Built for students and early-career talent &nbsp;•&nbsp; One workspace. A calmer mind.
            </p>
          </div>

          {/* ------------------------------------------------------------ */}
          {/* Career Road Illustration (Smooth blended bottom-right asset) */}
          {/* ------------------------------------------------------------ */}
          <div
            className="hidden lg:flex absolute right-0 bottom-0 w-[55%] lg:w-[57%] xl:w-[60%] max-w-[700px] 2xl:max-w-[760px] justify-end items-end pointer-events-none select-none z-0"
            style={{
              maskImage: 'radial-gradient(ellipse 110% 105% at 95% 95%, black 45%, rgba(0,0,0,0.85) 65%, rgba(0,0,0,0.35) 85%, transparent 100%)',
              WebkitMaskImage: 'radial-gradient(ellipse 110% 105% at 95% 95%, black 45%, rgba(0,0,0,0.85) 65%, rgba(0,0,0,0.35) 85%, transparent 100%)',
            }}
          >
            <img
              src={careerRoadImg}
              alt="Career roadmap illustration"
              className="w-full h-auto object-contain drop-shadow-none"
              draggable={false}
            />
          </div>
        </section>

        {/* -------------------------------------------------------------- */}
        {/* RIGHT SECTION (Clean White Google-Only Login Panel)            */}
        {/* -------------------------------------------------------------- */}
        <section className="w-full lg:w-[430px] xl:w-[460px] 2xl:w-[490px] bg-white border-t lg:border-t-0 lg:border-l border-[#E2E2E2] flex items-center justify-center p-6 sm:p-8 lg:p-6 xl:p-8 z-10 shrink-0 overflow-y-auto min-h-0">
          <div className="w-full max-w-[350px] xl:max-w-[370px]">
            {/* Card Header */}
            <h2 className="font-serif text-[26px] sm:text-[28px] font-bold text-[#111827] tracking-tight mb-0.5">
              Welcome back
            </h2>
            <p className="text-[13px] text-[#6B6B6B] mb-5">
              Sign in to your Aptly account
            </p>

            {/* If no account found banner */}
            {notFoundError && (
              <div className="mb-5 p-3.5 rounded-xl bg-amber-50/90 border border-amber-200/90 text-amber-900 text-xs animate-fade-in">
                <div className="flex items-start gap-2.5">
                  <AlertCircle size={16} className="text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold text-amber-950">No Aptly account found.</p>
                    <p className="mt-1 text-amber-800 leading-normal">
                      Please create an account first to start your journey.
                    </p>
                    <Link
                      to="/signup"
                      className="inline-flex items-center gap-1 font-semibold text-[#2B62C6] hover:underline mt-2"
                    >
                      Create one first <ArrowRight size={13} />
                    </Link>
                  </div>
                </div>
              </div>
            )}

            {/* General Google Error */}
            {googleError && !notFoundError && (
              <div className="mb-5 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-start gap-2 animate-fade-in">
                <AlertCircle size={15} className="shrink-0 mt-0.5 text-red-600" />
                <p>{googleError}</p>
              </div>
            )}

            {/* ---- Functional Google Sign-In Button ---- */}
            <div className="relative mb-5">
              {/* Pixel-matched Google Button Surface */}
              <button
                type="button"
                className="w-full h-[42px] rounded-lg bg-[#2B5FA8] hover:bg-[#255294] active:bg-[#1E437C] text-white flex items-center justify-center gap-2.5 transition-colors shadow-none font-medium text-[13.5px] select-none"
              >
                <div className="w-5 h-5 bg-white rounded-full flex items-center justify-center shrink-0 p-0.5">
                  <svg width="13" height="13" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17Z" />
                    <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24Z" />
                    <path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.16 0 9.97 0 12s.45 3.84 1.25 5.42l4.03-3.15Z" />
                    <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98Z" />
                  </svg>
                </div>
                <span>Sign in with Google</span>
              </button>

              {/* Functional Invisible GoogleLogin Overlay */}
              <div className="absolute inset-0 opacity-0 overflow-hidden cursor-pointer">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={handleGoogleError}
                  useOneTap={false}
                  shape="rectangular"
                  size="large"
                  width="370"
                />
              </div>
            </div>

            {/* Don't have an account link */}
            <p className="text-center text-[12.5px] text-[#6B6B6B]">
              Don&apos;t have an account?{' '}
              <Link
                to="/signup"
                id="create-account-btn"
                className="text-[#2B62C6] font-semibold hover:underline focus:underline focus:outline-none cursor-pointer transition-subtle"
              >
                Create one
              </Link>
            </p>

            {/* Loading Indicator */}
            {isLoading && (
              <div className="mt-3 flex items-center justify-center gap-2 text-xs text-[#6B6B6B] animate-fade-in">
                <div className="w-3.5 h-3.5 rounded-full border-2 border-[#2B62C6] border-t-transparent animate-spin" />
                Signing you in…
              </div>
            )}

            {/* Bottom Insight Card */}
            <div className="mt-6 p-3 rounded-xl bg-[#F8FAFC] border border-[#E8EEF5]">
              <div>
                <p className="text-[12px] text-[#475569] leading-relaxed">
                  A more focused, less overwhelming job search — powered by AI, built for you.
                </p>
                <div className="w-4 h-[1.5px] bg-[#94A3B8] mt-1.5" />
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

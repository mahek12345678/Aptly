import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { CareerJourneyLandscape } from '@/components/about/CareerJourneyLandscape';
import { AptlyLogo } from '@/components/common/AptlyLogo';

export default function AboutPage() {
  const navigate = useNavigate();

  const handleLearnMore = () => {
    const pillarsEl = document.getElementById('manifesto-pillars');
    if (pillarsEl) {
      pillarsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <DashboardLayout>
      <div className="w-full max-w-[1220px] mx-auto animate-fade-in">
        {/* ================================================== */}
        {/* SECTION 1 — HERO (Compact ~520-560px footprint)    */}
        {/* ================================================== */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 items-center pt-1 sm:pt-2 pb-10 sm:pb-12">
          {/* Left Hero Narrative (50% desktop) */}
          <div className="lg:col-span-6 flex flex-col justify-center">
            {/* Top small label */}
            <span className="text-[11px] font-semibold tracking-[0.24em] text-[#6B6B6B] uppercase mb-[14px] block">
              ABOUT APTLY
            </span>

            {/* Brand Title */}
            <div className="mb-[28px]">
              <AptlyLogo height={52} variant="full" />
            </div>

            {/* Main headline */}
            <h2 className="font-serif text-[32px] sm:text-[36px] lg:text-[40px] font-normal sm:font-medium text-[#1A1A1A] leading-[1.14] tracking-[-0.01em] mb-[22px]">
              A calmer way<br />
              to build your career.
            </h2>

            {/* Supporting copy */}
            <p className="text-[13.5px] sm:text-[14.5px] text-[#6B6B6B] leading-[1.6] max-w-[440px] mb-[28px] font-sans">
              Aptly helps you find the right opportunities, understand them deeply,
              tailor your resume with clarity, and stay in control of your entire
              application journey.
            </p>

            {/* Hero CTAs */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => navigate('/dashboard')}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#1B2A4A] hover:bg-[#142038] active:bg-[#0F182A] text-white text-[13px] font-medium transition-colors cursor-pointer shadow-2xs"
              >
                <span>Get Started</span>
                <ArrowRight size={14} className="stroke-[2.2]" />
              </button>

              <button
                type="button"
                onClick={handleLearnMore}
                className="inline-flex items-center px-5 py-2.5 rounded-lg bg-white hover:bg-[#F8FAFC] active:bg-[#F1F5F9] border border-[#E2E2E2] text-[#1A1A1A] text-[13px] font-medium transition-colors cursor-pointer shadow-2xs"
              >
                <span>Learn More</span>
              </button>
            </div>
          </div>

          {/* Right Hero Visual: Career Journey Landscape (50% desktop) */}
          <div className="lg:col-span-6 w-full flex items-center justify-center lg:justify-end">
            <CareerJourneyLandscape />
          </div>
        </section>

        {/* Thin horizontal divider */}
        <hr className="border-0 h-px bg-[#E2E2E2] my-0" />

        {/* ================================================== */}
        {/* SECTION 2 — PLAN · APPLY · GROW                     */}
        {/* ================================================== */}
        <section
          id="manifesto-pillars"
          className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-0 scroll-mt-16 py-10 sm:py-12"
        >
          {/* Pillar 01: Plan */}
          <div className="md:pr-8 lg:pr-10 md:border-r md:border-[#E2E2E2] flex flex-col justify-start">
            <span className="text-[12px] font-medium text-[#3D5580] tracking-wider mb-2 font-mono">
              01
            </span>
            <h3 className="font-serif text-[26px] sm:text-[30px] font-normal text-[#1B2A4A] mb-2.5 leading-tight">
              Plan
            </h3>
            <p className="text-[13.5px] text-[#6B6B6B] leading-[1.6]">
              Understand your profile, your strengths, and the opportunities that genuinely fit you.
            </p>
          </div>

          {/* Pillar 02: Apply */}
          <div className="md:px-8 lg:px-10 md:border-r md:border-[#E2E2E2] flex flex-col justify-start">
            <span className="text-[12px] font-medium text-[#3D5580] tracking-wider mb-2 font-mono">
              02
            </span>
            <h3 className="font-serif text-[26px] sm:text-[30px] font-normal text-[#1B2A4A] mb-2.5 leading-tight">
              Apply
            </h3>
            <p className="text-[13.5px] text-[#6B6B6B] leading-[1.6]">
              Analyze roles deeply, tailor your resume with factual precision, and move through applications with clarity.
            </p>
          </div>

          {/* Pillar 03: Grow */}
          <div className="md:pl-8 lg:pl-10 flex flex-col justify-start">
            <span className="text-[12px] font-medium text-[#3D5580] tracking-wider mb-2 font-mono">
              03
            </span>
            <h3 className="font-serif text-[26px] sm:text-[30px] font-normal text-[#1B2A4A] mb-2.5 leading-tight">
              Grow
            </h3>
            <p className="text-[13.5px] text-[#6B6B6B] leading-[1.6]">
              Track outcomes, learn from each stage, and make better career decisions over time.
            </p>
          </div>
        </section>

        {/* ================================================== */}
        {/* SECTION 3 — OUR MISSION                             */}
        {/* ================================================== */}
        <section className="mb-10 sm:mb-12">
          <div className="rounded-2xl border border-[#E2E2E2] bg-white p-7 sm:p-9 lg:p-11 shadow-2xs">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 items-center">
              {/* Left Statement */}
              <div className="lg:col-span-8 lg:border-r lg:border-[#E2E2E2] lg:pr-8">
                <span className="text-[11px] font-semibold tracking-[0.24em] text-[#6B6B6B] uppercase mb-3.5 block">
                  OUR MISSION
                </span>
                <h2 className="font-serif text-[26px] sm:text-[30px] lg:text-[34px] font-normal sm:font-medium text-[#1B2A4A] leading-[1.22] tracking-[-0.01em]">
                  To bring clarity, discipline, and intelligence<br className="hidden sm:inline" />
                  to every career journey.
                </h2>
              </div>

              {/* Right Emotional Close */}
              <div className="lg:col-span-4 flex items-center">
                <p className="text-[13.5px] text-[#6B6B6B] leading-[1.65] font-sans">
                  Aptly is built for people who care about doing meaningful work &mdash; and for a
                  future where career decisions are more informed, more intentional, and more human.
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </DashboardLayout>
  );
}

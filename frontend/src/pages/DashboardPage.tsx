import { useEffect, useMemo, useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/lib/api';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { DashboardApplicationIntentBanner } from '@/components/dashboard/DashboardApplicationIntentBanner';
import { DashboardMetricsStrip } from '@/components/dashboard/DashboardMetricsStrip';
import { PipelineVelocityChart } from '@/components/dashboard/PipelineVelocityChart';
import { SearchFunnelCard } from '@/components/dashboard/SearchFunnelCard';
import { UpcomingAgendaTimeline } from '@/components/dashboard/UpcomingAgendaTimeline';
import { RecentActivity } from '@/components/dashboard/RecentActivity';
import { DashboardMatchesLedger } from '@/components/dashboard/DashboardMatchesLedger';
import {
  DashboardSummaryResponse,
  RecentActivityItem,
  UpcomingReminderItem,
} from '@/types/dashboard';
import { JobApplication } from '@/types/application';

export default function DashboardPage() {
  const { user } = useAuth();
  const [summaryData, setSummaryData] = useState<DashboardSummaryResponse | null>(null);
  const [applications, setApplications] = useState<JobApplication[]>([]);

  // Fetch live dashboard metrics, activity, reminders, and applications
  const loadDashboardData = useCallback(() => {
    // 1. Fetch summary metrics & activity
    api
      .get<DashboardSummaryResponse>('/api/v1/dashboard/summary')
      .then((data) => {
        if (data) setSummaryData(data);
      })
      .catch((err) => {
        console.error('Failed to load dashboard summary:', err);
      });

    // 2. Fetch all user applications for velocity visualization & funnel calculations
    api
      .get<JobApplication[]>('/api/v1/applications')
      .then((apps) => {
        if (Array.isArray(apps)) setApplications(apps);
      })
      .catch((err) => {
        console.error('Failed to load user applications for dashboard:', err);
      });
  }, []);

  useEffect(() => {
    loadDashboardData();

    // Re-sync whenever an application is confirmed or updated
    const handleApplicationConfirmed = () => {
      loadDashboardData();
    };

    window.addEventListener('aptly:application-confirmed', handleApplicationConfirmed);

    return () => {
      window.removeEventListener('aptly:application-confirmed', handleApplicationConfirmed);
    };
  }, [loadDashboardData]);

  // Extract user's first name dynamically
  const displayName = summaryData?.user?.first_name || summaryData?.user?.name || user?.name;
  const firstName = useMemo(() => {
    if (!displayName) return 'there';
    const first = displayName.trim().split(' ')[0];
    return first.charAt(0).toUpperCase() + first.slice(1);
  }, [displayName]);

  // Compute live headline metrics from real data
  const jobsApplied = summaryData?.metrics?.jobs_applied ?? applications.length;
  const repliesReceived =
    summaryData?.metrics?.replies_received ??
    applications.filter((a) => a.status && a.status.toLowerCase() !== 'applied').length;
  const offersReceived =
    summaryData?.metrics?.offers_received ??
    applications.filter((a) => a.status && a.status.toLowerCase() === 'offer').length;

  // Applications added in the last 7 days
  const thisWeekCount = useMemo(() => {
    const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    return applications.filter((app) => {
      const d = app.applied_at || app.created_at;
      return d ? new Date(d) >= sevenDaysAgo : false;
    }).length;
  }, [applications]);

  // Map live recent activity items
  const recentActivityItems: RecentActivityItem[] = useMemo(() => {
    if (!summaryData?.recent_activity) return [];
    return summaryData.recent_activity.map((item) => ({
      id: item.id,
      company: item.company,
      role: item.role,
      status: item.status,
      updatedAt: item.updated_at,
      updatedAtIso: item.updated_at_iso,
      deadline: item.deadline,
      companyId: item.company.toLowerCase(),
    }));
  }, [summaryData?.recent_activity]);

  // Map live upcoming reminders
  const reminderItems: UpcomingReminderItem[] = useMemo(() => {
    if (!summaryData?.upcoming_reminders) return [];
    return summaryData.upcoming_reminders.map((r) => ({
      id: r.id,
      title: r.title,
      dueText: r.due_text,
      dueDate: r.due_date,
      type: r.type,
      company: r.company,
    }));
  }, [summaryData?.upcoming_reminders]);

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-[1360px] mx-auto px-4 sm:px-6 lg:px-8 py-6 animate-fade-in">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-3">
          <div>
            <h1 className="font-serif text-[28px] sm:text-[34px] font-bold text-[#1A1A1A] tracking-tight leading-tight">
              Welcome back, {firstName}.
            </h1>
            <p className="text-[13.5px] sm:text-[14px] text-[#6B6B6B] mt-1">
              Here&apos;s where your search stands today.
            </p>
          </div>

          <div className="shrink-0 self-start sm:self-auto">
            <span className="font-mono text-[9.5px] text-[#6B6B6B] border border-[#E2E2E2] bg-white px-2.5 py-1 rounded tracking-wider font-semibold uppercase shadow-2xs">
              PIPELINE VELOCITY ACTIVE
            </span>
          </div>
        </div>

        {/* Pending Application Intent Banner (conditionally displayed if intent active) */}
        <DashboardApplicationIntentBanner />

        {/* Continuous Horizontal Metrics Strip */}
        <DashboardMetricsStrip
          jobsApplied={jobsApplied}
          repliesReceived={repliesReceived}
          offersReceived={offersReceived}
          thisWeekCount={thisWeekCount}
        />

        {/* 2-Column Analytical Ledger Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column (7 cols, ~58% width): Pipeline Velocity Chart & Upcoming Agenda */}
          <div className="lg:col-span-7 space-y-6">
            <PipelineVelocityChart applications={applications} />
            <UpcomingAgendaTimeline
              reminders={reminderItems}
              applications={applications}
            />
          </div>

          {/* Right Column (5 cols, ~42% width): Search Funnel, Recent Activity & Your Matches */}
          <div className="lg:col-span-5 space-y-6">
            <SearchFunnelCard applications={applications} />
            <RecentActivity items={recentActivityItems} />
            <DashboardMatchesLedger
              totalMatchesCount={summaryData?.job_matches_count}
            />
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}

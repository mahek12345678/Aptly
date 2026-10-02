export interface MetricData {
  id: string;
  title: string;
  value: number;
  trend: string;
  trendDirection: 'up' | 'down' | 'neutral';
  iconType: 'document' | 'message' | 'briefcase';
  color: 'blue' | 'green' | 'amber';
}

export type ApplicationStatus =
  | 'Applied'
  | 'Reply Received'
  | 'OA/Assessment'
  | 'Interview'
  | 'Offer Received'
  | 'Rejected';

export interface RecentActivityItem {
  id: string;
  company: string;
  role: string;
  status: ApplicationStatus;
  updatedAt: string;
  updatedAtIso?: string;
  deadline?: string | null;
  companyId?: 'google' | 'amazon' | 'microsoft' | 'flipkart' | 'nvidia' | string;
}

export interface UpcomingReminderItem {
  id: string;
  title: string;
  dueText: string;
  dueDate?: string;
  type: 'application' | 'assessment' | 'followup' | 'interview';
  company?: string;
}

export interface DashboardSummaryResponse {
  user: {
    name: string;
    first_name?: string;
    profile_picture_url?: string | null;
  };
  metrics: {
    jobs_applied: number;
    replies_received: number;
    offers_received: number;
  };
  recent_activity: {
    id: string;
    company: string;
    role: string;
    status: ApplicationStatus;
    raw_status?: string;
    updated_at: string;
    updated_at_iso?: string;
    deadline?: string | null;
  }[];
  upcoming_reminders: {
    id: string;
    title: string;
    due_text: string;
    due_date?: string;
    type: 'application' | 'assessment' | 'followup' | 'interview';
    company?: string;
  }[];
  job_matches_count?: number;
}

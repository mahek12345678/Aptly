export type ApplicationStatus = 'applied' | 'oa' | 'interview' | 'offer' | 'rejected';
export type TrackingState = 'application_started' | 'applied';

export interface JobApplication {
  id: string;
  user_id: string;
  company: string;
  role: string;
  location?: string | null;
  deadline?: string | null;
  stipend?: string | null;
  status: ApplicationStatus;
  application_url?: string | null;
  job_description?: string | null;
  notes?: string | null;
  source?: string | null;
  source_job_id?: string | null;
  tracking_state?: TrackingState;
  application_started_at?: string | null;
  applied_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationStartPayload {
  company: string;
  role: string;
  location?: string | null;
  deadline?: string | null;
  compensation?: string | null;
  job_description?: string | null;
  application_url?: string | null;
  source?: string;
  source_job_id?: string | null;
}

export interface CreateApplicationPayload {
  company: string;
  role: string;
  location?: string;
  deadline?: string | null;
  stipend?: string;
  status?: ApplicationStatus;
  application_url?: string;
  job_description?: string;
  notes?: string;
  source?: string;
}

export interface UpdateApplicationPayload {
  company?: string;
  role?: string;
  location?: string | null;
  deadline?: string | null;
  stipend?: string | null;
  status?: ApplicationStatus;
  application_url?: string | null;
  job_description?: string | null;
  notes?: string | null;
  source?: string | null;
}

export interface KanbanStage {
  id: ApplicationStatus;
  label: string;
  color: string;
  dotColor: string;
  badgeBg: string;
  badgeText: string;
  headerBg?: string;
  headerBorder?: string;
  countBg?: string;
  countText?: string;
}

export const KANBAN_STAGES: KanbanStage[] = [
  {
    id: 'applied',
    label: 'Applied',
    color: '#9CA3AF',
    dotColor: '#9CA3AF',
    badgeBg: '#F3F4F6',
    badgeText: '#4B5563',
    headerBg: '#F9FAFB',
    headerBorder: '#E5E7EB',
    countBg: '#E5E7EB',
    countText: '#4B5563',
  },
  {
    id: 'oa',
    label: 'OA/Assessment',
    color: '#6B7A99',
    dotColor: '#6B7A99',
    badgeBg: '#EFF2F7',
    badgeText: '#475569',
    headerBg: '#EFF2F7',
    headerBorder: '#DCE4EE',
    countBg: '#DFE7F2',
    countText: '#334661',
  },
  {
    id: 'interview',
    label: 'Interview',
    color: '#D6A84B',
    dotColor: '#D6A84B',
    badgeBg: '#FFF8E7',
    badgeText: '#1B2A4A',
    headerBg: '#FFF8E7',
    headerBorder: '#F1E3BD',
    countBg: '#F8ECC8',
    countText: '#1B2A4A',
  },
  {
    id: 'offer',
    label: 'Offer',
    color: '#4F8A64',
    dotColor: '#4F8A64',
    badgeBg: '#EDF8F0',
    badgeText: '#1B2A4A',
    headerBg: '#EDF8F0',
    headerBorder: '#D4EADB',
    countBg: '#D8F0E0',
    countText: '#1B2A4A',
  },
  {
    id: 'rejected',
    label: 'Rejected',
    color: '#7A2E2E',
    dotColor: '#7A2E2E',
    badgeBg: '#FDF2F2',
    badgeText: '#7A2E2E',
    headerBg: '#FDF2F2',
    headerBorder: '#FADADA',
    countBg: '#F8D2D2',
    countText: '#7A2E2E',
  },
];

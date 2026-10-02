export interface JobListingDetail {
  id: string;
  company: string;
  role_title: string;
  location: string | null;
  employment_type: string | null;
  description: string;
  application_url: string | null;
  deadline: string | null;
  compensation: string | null;
  posted_at: string | null;
  source: string;
}

export interface JobMatchItem {
  id: string;
  similarity_score: number;
  preference_score: number;
  final_score: number;
  match_reasons: string[];
  saved: boolean;
  dismissed: boolean;
  matched_at: string;
  job: JobListingDetail;
}

export interface JobMatchesListResponse {
  items: JobMatchItem[];
  total: number;
  page: number;
  limit: number;
  last_refreshed_at: string | null;
}

export interface RefreshMatchesResponse {
  task_id?: string | null;
  status: string;
  refreshed_count: number;
  matches_count: number;
  refreshed_at: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: string;
  ready: boolean;
  result?: Record<string, unknown> | null;
  error?: string | null;
}

export interface ToggleSaveResponse {
  id: string;
  saved: boolean;
}

export interface DismissMatchResponse {
  id: string;
  dismissed: boolean;
}

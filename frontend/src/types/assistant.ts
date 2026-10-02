export interface SuggestedAction {
  label: string;
  route: string;
}

export interface AssistantQueryRequest {
  message: string;
  page_context?: string;
}

export interface AssistantQueryResponse {
  answer: string;
  intent: string;
  voice_available: boolean;
  suggested_actions: SuggestedAction[];
}

export interface BriefingSummaryBlock {
  active_matches_count: number;
  upcoming_oa_count: number;
  upcoming_interviews_count: number;
  deadlines_7d_count: number;
  pending_confirmations_count: number;
  top_matches: Array<{
    company: string;
    role: string;
    score_pct?: number;
    reasons?: string[];
  }>;
  upcoming_deadlines: Array<{
    company: string;
    role: string;
    deadline: string;
    status: string;
  }>;
}

export interface AssistantBriefingResponse {
  answer: string;
  intent: string;
  summary: BriefingSummaryBlock;
  voice_available: boolean;
  suggested_actions: SuggestedAction[];
}

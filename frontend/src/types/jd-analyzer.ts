export interface JobDetails {
  company: string;
  role_title: string;
  role_summary?: string;
  seniority?: string | null;
  location?: string | null;
  employment_type?: string | null;
  deadline?: string | null;
  compensation?: string | null;
  graduation_year_eligibility?: string | null;
  application_url?: string | null;
  required_skills: string[];
  preferred_skills: string[];
  required_experience?: string[];
  min_years_experience?: number | null;
  experience_requirements?: string | null;
  education_requirements?: string[];
  domain_requirements?: string[];
  tools_and_technologies?: string[];
  soft_skills?: string[];
  responsibilities: string[];
  qualifications: string[];
  keywords: string[];
  analysis_quality?: string;
  description_quality?: 'FULL' | 'COMPLETE' | 'PARTIAL' | 'INSUFFICIENT' | string;
  description_source?: 'ADZUNA_FULL' | 'ADZUNA_PREVIEW' | 'USER_PASTED' | 'OTHER_SUPPORTED_SOURCE' | 'PROVIDER_CANONICAL' | 'PROVIDER_PARTIAL' | string;
  description_length?: number;
  provider_description_length?: number | null;
  analysis_description_length?: number;
  is_truncated?: boolean;
  quality_warning?: string | null;
  internal_grade?: string | null;
  source?: string | null;
  source_job_id?: string | null;
}

export interface MatchBreakdown {
  required_skills_score: number | null;  // null = not evaluated (no requirements identified)
  preferred_skills_score: number | null; // null = not evaluated
  experience_score: number;
  domain_score: number;
  seniority_gap: boolean;
  analysis_quality?: string; // "COMPLETE" | "PARTIAL" | "INSUFFICIENT_REQUIREMENTS"
}

export interface SeniorityAlignment {
  seniority_requested: string;
  candidate_seniority: string;
  gap?: string;
  status: string;
  is_gap: boolean;
}

export interface VerifiedMatchItem {
  requirement: string;
  canonical_requirement: string;
  status: 'VERIFIED_MATCH' | 'RELATED_EVIDENCE' | 'NOT_FOUND';
  evidence: string[];
  notes: string;
  is_required: boolean;
}

export interface NormalizedRequirementItem {
  requirement_id: string;
  category: 'required_skill' | 'preferred_skill' | 'experience' | 'education' | 'domain' | 'other' | 'soft_skill';
  requirement: string;
  canonical: string;
  importance: 'required' | 'preferred';
  score_component?: string;
  match_status: 'verified' | 'related' | 'missing';
  resume_evidence: string[];
  source: string;
  source_excerpt?: string;
  notes: string;
  weight: number;
}

export interface GapBreakdownItem {
  requirement_id?: string;
  requirement: string;
  canonical_requirement?: string;
  status?: string;
  source?: string;
  advice: string;
  is_required?: boolean;
  score_component?: string;
  category?: string;
}

export interface MatchAnalysis {
  overall_match_score: number | null;
  analysis_quality?: string;           // "COMPLETE" | "PARTIAL" | "INSUFFICIENT_REQUIREMENTS"
  description_quality?: 'FULL' | 'COMPLETE' | 'PARTIAL' | 'INSUFFICIENT' | string;
  description_source?: 'ADZUNA_FULL' | 'ADZUNA_PREVIEW' | 'USER_PASTED' | 'OTHER_SUPPORTED_SOURCE' | 'PROVIDER_CANONICAL' | 'PROVIDER_PARTIAL' | string;
  description_length?: number;
  provider_description_length?: number | null;
  analysis_description_length?: number;
  is_truncated?: boolean;
  insufficient_requirements?: boolean; // true when we couldn't extract enough JD requirements
  matched_skills: string[];
  missing_skills: string[];
  relevant_projects: string[];
  relevant_experience: string[];
  strengths: string[];
  gaps: string[];
  technical_gaps?: GapBreakdownItem[];
  unverified_traits?: GapBreakdownItem[];
  eligibility_review?: GapBreakdownItem[];
  match_breakdown?: MatchBreakdown | null;
  seniority_alignment?: SeniorityAlignment | null;
  verified_matches?: VerifiedMatchItem[];
  related_experience?: VerifiedMatchItem[];
  gaps_breakdown?: GapBreakdownItem[];
  verified_count?: number;
  related_count?: number;
  gap_count?: number;
  gaps_summary_message?: string | null;
  normalized_requirements?: NormalizedRequirementItem[];
}

export interface AnalyzeJDResponse {
  job_details: JobDetails;
  match_analysis: MatchAnalysis;
  resume_id: string;
  resume_filename: string;
}

export interface TailoredSummary {
  suggestion: string;
  strategy?: string | null;
}

export interface TailoredSkills {
  prioritized: string[];
  secondary: string[];
  target_gaps?: string[];
  strategy?: string | null;
}

export interface TailoredEntry {
  original_entry: string;
  action_suggestion: string;
  supports?: string[];
  related_evidence?: string[];
  does_not_establish?: string[];
  keywords_to_bold: string[];
  project_id?: string;
  project_title?: string;
  project_bullets?: string[];
}

export interface TailoredSections {
  summary: TailoredSummary;
  skills: TailoredSkills;
  experience: TailoredEntry[];
  projects: TailoredEntry[];
}

export interface TailorResumeResponse {
  tailored_sections: TailoredSections;
  resume_id: string;
}

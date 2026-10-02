import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Pencil,
  FileText,
  Eye,
  RefreshCw,
  ArrowRight,
  LogOut,
  Lightbulb,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/lib/api';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import {
  EditProfileDrawer,
  ProfilePreferences,
  ProfilePersonalization,
} from '@/components/profile/EditProfileDrawer';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ResumeProject {
  project_id?: string;
  title: string;
  technologies: string[];
  bullets: string[];
  links?: string[];
  description?: string;
}

interface ExperienceEntry {
  company: string;
  role: string;
  location?: string;
  dates: string;
  start_date?: string;
  end_date?: string;
  bullets: string[];
}

interface EducationEntry {
  institution?: string;
  degree?: string;
  grad_year?: string;
  dates?: string;
  entry?: string;
}

interface ParsedResumeData {
  id: string;
  file_name: string;
  file_size_bytes?: number | null;
  mime_type?: string | null;
  parsed_status: string;
  created_at: string;
  parsed_at?: string | null;
  parsed_data?: {
    name?: string | null;
    headline?: string | null;
    email?: string | null;
    phone?: string | null;
    education?: (string | EducationEntry)[];
    skills?: string[];
    skill_categories?: Record<string, string[]>;
    experience?: (string | ExperienceEntry)[];
    projects?: (ResumeProject | string)[];
    certifications?: string[];
    achievements?: string[];
    raw_text?: string;
  } | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function cleanExtractedText(text?: string | null): string {
  if (!text) return '';
  let t = text.replace(/(\b\w+)-\s*\n\s*(\w+\b)/g, '$1-$2');
  t = t.replace(/(\b\w+)\s*\n\s*(\w+\b)/g, '$1 $2');
  t = t.replace(/[ \t]+/g, ' ');
  t = t.replace(/\s*\n\s*/g, ' ');
  t = t.replace(/^[#*_\-\s|•▪–—>:]+|[#*_\-\s|•▪–—>:]+$/g, '');
  return t.trim();
}

function getInitials(name?: string | null): string {
  if (!name || /^home$/i.test(name.trim())) return 'AM';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function formatRelativeTime(dateStr?: string | null): string {
  if (!dateStr) return 'Recently';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return 'Recently';
  const now = new Date();
  const diffHours = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60));
  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return '1 day ago';
  if (diffDays < 30) return `${diffDays} days ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatDisplayDate(dateStr?: string | null): string {
  if (!dateStr) return 'Oct 2';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return 'Oct 2';
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Canonical keyword sets for deterministic skill classification
const LANGUAGE_KEYWORDS = [
  'python', 'c++', 'cpp', 'c', 'c#', 'java', 'javascript', 'typescript', 'go', 'golang',
  'rust', 'ruby', 'php', 'swift', 'kotlin', 'scala', 'r', 'html', 'css', 'bash', 'shell'
];

const BACKEND_KEYWORDS = [
  'fastapi', 'rest api', 'rest apis', 'rest api design', 'authentication', 'session management',
  'docker', 'kubernetes', 'django', 'flask', 'node.js', 'nodejs', 'express', 'express.js',
  'spring', 'spring boot', 'graphql', 'grpc', 'microservices', 'jwt', 'oauth', 'celery', 'websockets'
];

const DATA_KEYWORDS = [
  'postgresql', 'postgres', 'sql', 'sqlalchemy', 'sqlalchemy (orm)', 'relational schema design',
  'redis', 'sqlite', 'mongodb', 'mysql', 'chromadb', 'pandas', 'numpy', 'scikit-learn',
  'pytorch', 'tensorflow', 'vector store', 'vector database', 'data pipelines', 'kafka', 'database indexing', 'caching'
];

const TOOLS_CLOUD_KEYWORDS = [
  'git', 'github', 'docker', 'linux', 'aws', 'aws ec2/s3', 'railway', 'postman', 'pytest',
  'ci/cd', 'kubernetes', 'gcp', 'azure', 'terraform', 'vercel'
];

export interface CanonicalSkillGroup {
  key: string;
  title: string;
  skills: string[];
}

function normalizeCategoryKey(cat: string): { key: string; title: string } {
  const c = cat.toLowerCase().replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '_').trim();
  if (c.includes('lang')) return { key: 'languages', title: 'Languages' };
  if (c.includes('backend') || c.includes('web')) return { key: 'backend_web', title: 'Backend & Web' };
  if (c.includes('data') || c.includes('database') || c.includes('system')) return { key: 'data_systems', title: 'Data & Systems' };
  if (c.includes('tool') || c.includes('cloud') || c.includes('devop')) return { key: 'tools_cloud', title: 'Tools & Cloud' };
  if (c.includes('engineer') || c.includes('practice') || c.includes('method')) return { key: 'engineering', title: 'Engineering Practices' };
  return {
    key: c,
    title: cat.trim(),
  };
}

function assignSkillCategory(skill: string): string {
  const s = skill.toLowerCase().trim();
  // SQL and database tools strictly belong to data_systems
  if (s === 'sql' || DATA_KEYWORDS.some((k) => s === k || s.includes(k))) {
    return 'data_systems';
  }
  if (BACKEND_KEYWORDS.some((k) => s === k || s.includes(k))) {
    return 'backend_web';
  }
  if (TOOLS_CLOUD_KEYWORDS.some((k) => s === k || s.includes(k))) {
    return 'tools_cloud';
  }
  if (LANGUAGE_KEYWORDS.some((k) => s === k || s.includes(k))) {
    return 'languages';
  }
  return 'backend_web';
}

function buildCanonicalSkillsAndGroups(
  rawSkills: string[],
  resumeCategories?: Record<string, string[]> | null
): { canonicalSkills: string[]; skillGroups: CanonicalSkillGroup[] } {
  const groupOrder = ['languages', 'backend_web', 'data_systems', 'tools_cloud', 'engineering'];
  const groupMap = new Map<string, { title: string; skills: string[] }>();
  groupMap.set('languages', { title: 'Languages', skills: [] });
  groupMap.set('backend_web', { title: 'Backend & Web', skills: [] });
  groupMap.set('data_systems', { title: 'Data & Systems', skills: [] });
  groupMap.set('tools_cloud', { title: 'Tools & Cloud', skills: [] });
  groupMap.set('engineering', { title: 'Engineering Practices', skills: [] });

  const seenSkillsLower = new Set<string>();
  const canonicalSkills: string[] = [];

  const addSkillToGroup = (groupKey: string, skill: string) => {
    const clean = cleanExtractedText(skill);
    if (!clean) return;
    const lower = clean.toLowerCase();
    if (seenSkillsLower.has(lower)) return;

    let finalKey = groupKey;
    // Canonical rule: SQL belongs strictly to data_systems
    if (lower === 'sql') {
      finalKey = 'data_systems';
    } else if (!groupMap.has(finalKey)) {
      finalKey = assignSkillCategory(clean);
    }

    if (!groupMap.has(finalKey)) {
      groupMap.set(finalKey, { title: cleanExtractedText(groupKey), skills: [] });
    }

    seenSkillsLower.add(lower);
    canonicalSkills.push(clean);
    groupMap.get(finalKey)!.skills.push(clean);
  };

  // 1. Process parsed resume categories if present
  if (resumeCategories && Object.keys(resumeCategories).length > 0) {
    for (const [catName, catSkills] of Object.entries(resumeCategories)) {
      const { key } = normalizeCategoryKey(catName);
      if (Array.isArray(catSkills)) {
        for (const sk of catSkills) {
          addSkillToGroup(key, sk);
        }
      }
    }
  }

  // 2. Process any remaining raw skills
  for (const sk of rawSkills) {
    const targetKey = assignSkillCategory(sk);
    addSkillToGroup(targetKey, sk);
  }

  // 3. Format final unique group list in canonical order
  const skillGroups: CanonicalSkillGroup[] = [];
  for (const key of groupOrder) {
    const grp = groupMap.get(key);
    if (grp && grp.skills.length > 0) {
      skillGroups.push({
        key,
        title: grp.title,
        skills: grp.skills,
      });
      groupMap.delete(key);
    }
  }

  for (const [key, grp] of groupMap.entries()) {
    if (grp.skills.length > 0) {
      skillGroups.push({
        key,
        title: grp.title,
        skills: grp.skills,
      });
    }
  }

  return { canonicalSkills, skillGroups };
}

// ---------------------------------------------------------------------------
// Main Profile Component
// ---------------------------------------------------------------------------

export default function ProfilePage() {
  const { user, logout, refreshUser } = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [preferences, setPreferences] = useState<ProfilePreferences | null>(null);
  const [personalization, setPersonalization] = useState<ProfilePersonalization | null>(null);
  const [resume, setResume] = useState<ParsedResumeData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isReplacingResume, setIsReplacingResume] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [avatarError, setAvatarError] = useState(false);
  const [isOpeningResume, setIsOpeningResume] = useState(false);
  const [resumeActionError, setResumeActionError] = useState<string | null>(null);

  // Fetch canonical user data
  const fetchData = async () => {
    try {
      const [prefsRes, persRes, resumeRes] = await Promise.allSettled([
        api.get<ProfilePreferences>('/api/onboarding/preferences'),
        api.get<ProfilePersonalization>('/api/onboarding/personalization'),
        api.get<ParsedResumeData>('/api/resumes/current/parsed'),
      ]);

      if (prefsRes.status === 'fulfilled') {
        setPreferences(prefsRes.value);
      }
      if (persRes.status === 'fulfilled') {
        setPersonalization(persRes.value);
      }
      if (resumeRes.status === 'fulfilled') {
        setResume(resumeRes.value);
      } else {
        try {
          const rawResume = await api.get<ParsedResumeData>('/api/resumes/current');
          setResume(rawResume);
        } catch {
          setResume(null);
        }
      }
    } catch (err) {
      console.error('Error fetching profile data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Keyboard shortcut Cmd+P / Ctrl+P
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'p') {
        e.preventDefault();
        setIsDrawerOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Canonical skill derivation: Single source of truth for counts, groups, and capability map
  const { canonicalSkills, skillGroups } = useMemo(() => {
    return buildCanonicalSkillsAndGroups(
      resume?.parsed_data?.skills || [],
      resume?.parsed_data?.skill_categories
    );
  }, [resume]);

  // Clean structured projects: unique parent projects only
  const structuredProjects: ResumeProject[] = useMemo(() => {
    if (!resume?.parsed_data?.projects) return [];
    const projs = resume.parsed_data.projects;
    const cleanList: ResumeProject[] = [];
    const seenTitles = new Set<string>();

    for (let i = 0; i < projs.length; i++) {
      const item = projs[i];
      let title = '';
      let technologies: string[] = [];
      let bullets: string[] = [];
      let description = '';

      if (typeof item === 'object' && item !== null) {
        title = cleanExtractedText(item.title || item.project_id || `Project ${i + 1}`);
        technologies = (Array.isArray(item.technologies) ? item.technologies : []).map(cleanExtractedText).filter(Boolean);
        bullets = (Array.isArray(item.bullets) ? item.bullets : []).map(cleanExtractedText).filter(Boolean);
        description = cleanExtractedText(item.description);
      } else if (typeof item === 'string') {
        const parts = item.split('|').map((s) => cleanExtractedText(s));
        title = parts[0] || `Project ${i + 1}`;
        technologies = parts[1] ? parts[1].split(/[,•]+/).map((t) => cleanExtractedText(t)).filter(Boolean) : [];
        bullets = parts.slice(2).map(cleanExtractedText).filter(Boolean);
      }

      if (!title || /^(achievements?|leadership|skills?|education|experience|technical skills)/i.test(title)) {
        continue;
      }

      const normTitle = title.toLowerCase().replace(/[^a-z0-9]/g, '');
      if (seenTitles.has(normTitle)) continue;
      seenTitles.add(normTitle);

      cleanList.push({
        title,
        technologies,
        bullets,
        description,
      });
    }

    return cleanList;
  }, [resume]);

  // Clean structured experiences
  const structuredExperiences: ExperienceEntry[] = useMemo(() => {
    if (!resume?.parsed_data?.experience) return [];
    const expList = resume.parsed_data.experience;
    const cleanList: ExperienceEntry[] = [];

    for (const item of expList) {
      if (typeof item === 'object' && item !== null) {
        cleanList.push({
          company: cleanExtractedText(item.company || 'Organization'),
          role: cleanExtractedText(item.role || 'Software Engineering Intern'),
          location: item.location ? cleanExtractedText(item.location) : undefined,
          dates: cleanExtractedText(item.dates || ''),
          start_date: item.start_date,
          end_date: item.end_date,
          bullets: (item.bullets || []).map(cleanExtractedText).filter(Boolean),
        });
      } else if (typeof item === 'string') {
        const lines = item.split('\n').map((l) => l.trim()).filter(Boolean);
        const header = lines[0] || '';
        const parts = header.split(/[·•–—|]+/).map((s) => cleanExtractedText(s));
        cleanList.push({
          company: parts[0] || 'Organization',
          role: parts[1] || 'Intern / Contributor',
          dates: parts[2] || '',
          bullets: lines.slice(1).map((b) => cleanExtractedText(b.replace(/^[-*•▪–—>\s]+/, ''))).filter(Boolean),
        });
      }
    }

    return cleanList;
  }, [resume]);

  // University & Education Inference
  const educationDisplay = useMemo(() => {
    const eduList = resume?.parsed_data?.education || [];
    let institution = '';
    let gradYear = '';
    let degree = '';

    if (eduList.length > 0) {
      const first = eduList[0];
      if (typeof first === 'object' && first !== null) {
        institution = cleanExtractedText(first.institution || '');
        gradYear = cleanExtractedText(first.grad_year || '');
        degree = cleanExtractedText(first.degree || '');
      } else if (typeof first === 'string') {
        const clean = cleanExtractedText(first);
        const dashMatch = clean.match(/[\u2014\u2013\u2012–—]|\s+-\s+|\|/);
        institution = dashMatch ? clean.slice(0, dashMatch.index).trim() : clean.split(',')[0].trim();
        const yearMatch = clean.match(/\b(202[4-9]|203[0-5])\b/);
        if (yearMatch) gradYear = yearMatch[1];
      }
    }

    if (!institution || /^(home|university|college|null|undefined)$/i.test(institution)) {
      institution = 'National Institute of Technology, Surat';
    }
    if (!gradYear) {
      gradYear = preferences?.graduation_year ? String(preferences.graduation_year) : '2027';
    }

    const location = preferences?.preferred_location || 'Bengaluru, India';

    return {
      institution,
      gradYear,
      degree,
      location,
    };
  }, [resume, preferences]);

  // Canonical candidate name: authenticated user unless placeholder ('Home', etc.), in which case current resume name
  const candidateName = useMemo(() => {
    const rawUser = user?.name?.trim();
    const isPlaceholder = !rawUser || /^(home|user|admin|test|null|undefined)$/i.test(rawUser);

    if (!isPlaceholder) {
      return rawUser;
    }

    const resumeName = resume?.parsed_data?.name?.trim();
    if (resumeName) {
      return resumeName
        .toLowerCase()
        .split(/\s+/)
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');
    }

    return 'Aarav Mehta';
  }, [user, resume]);

  // Candidate primary role / headline
  const candidateRole = useMemo(() => {
    if (resume?.parsed_data?.headline) {
      return resume.parsed_data.headline.split('|')[0].trim();
    }
    if (preferences?.preferred_roles && preferences.preferred_roles.length > 0) {
      return preferences.preferred_roles[0];
    }
    if (structuredExperiences.length > 0 && structuredExperiences[0].role) {
      return structuredExperiences[0].role;
    }
    return 'Software Engineer';
  }, [resume, preferences, structuredExperiences]);

  // Deterministic Profile Readiness
  const readiness = useMemo(() => {
    const hasResume = Boolean(resume?.id && resume.parsed_status === 'parsed');
    const hasSkills = canonicalSkills.length > 0;
    const hasRoles = Boolean(preferences?.preferred_roles && preferences.preferred_roles.length > 0);
    const hasOpportunity = Boolean(preferences?.opportunity_type || preferences?.user_type);
    const hasLocation = Boolean(preferences?.preferred_location);

    const resumeAndSkills = hasResume && hasSkills;
    const completed = [resumeAndSkills, hasRoles, hasOpportunity, hasLocation].filter(Boolean).length;
    const percentage = Math.round((completed / 4) * 100);

    return {
      completed,
      total: 4,
      percentage,
      hasResume: resumeAndSkills,
      hasRoles,
      hasOpportunity,
      hasLocation,
    };
  }, [resume, canonicalSkills, preferences]);

  // Empirical capability map: derives evidence from skills, projects, experience, and achievements
  const capabilityMap = useMemo(() => {
    const allSkills = canonicalSkills.map((s) => s.toLowerCase());
    const projectText = structuredProjects
      .map((p) => `${p.title} ${p.technologies.join(' ')} ${p.bullets.join(' ')}`)
      .join(' ')
      .toLowerCase();
    const experienceText = structuredExperiences
      .map((e) => `${e.company} ${e.role} ${e.bullets.join(' ')}`)
      .join(' ')
      .toLowerCase();
    const achievements = (resume?.parsed_data?.achievements || []).map((a) =>
      typeof a === 'string' ? a.toLowerCase() : JSON.stringify(a).toLowerCase()
    ).join(' ');

    const checkDomain = (keywords: string[]) => {
      const skillHit = allSkills.some((s) => keywords.some((k) => s.includes(k)));
      const projectHit = keywords.some((k) => projectText.includes(k));
      const expHit = keywords.some((k) => experienceText.includes(k));
      const achHit = keywords.some((k) => achievements.includes(k));

      const evidenceSources = [skillHit, projectHit, expHit, achHit].filter(Boolean).length;

      if (evidenceSources >= 3) {
        return { label: 'Strong Evidence', width: '92%', color: 'bg-[#1B2A4A]' };
      }
      if (evidenceSources === 2) {
        return { label: 'Moderate Evidence', width: '68%', color: 'bg-[#2B3E60]' };
      }
      if (evidenceSources === 1) {
        return { label: 'Some Evidence', width: '38%', color: 'bg-[#6B7F9E]' };
      }
      return { label: 'Limited Evidence', width: '18%', color: 'bg-[#94A3B8]' };
    };

    return [
      {
        name: 'Backend Engineering',
        ...checkDomain(['fastapi', 'rest api', 'rest', 'api', 'django', 'flask', 'node', 'express', 'docker', 'python', 'jwt', 'backend']),
      },
      {
        name: 'Problem Solving',
        ...checkDomain(['algorithm', 'dsa', 'data structures', 'leetcode', 'codeforces', 'c++', 'java', 'competitive', 'problem solving']),
      },
      {
        name: 'System Design',
        ...checkDomain(['distributed', 'task queue', 'redis', 'kafka', 'scalability', 'websockets', 'observability', 'concurrency', 'latency']),
      },
      {
        name: 'Data & Databases',
        ...checkDomain(['postgresql', 'postgres', 'sql', 'redis', 'mongodb', 'sqlalchemy', 'caching', 'indexing', 'database']),
      },
      {
        name: 'Frontend Development',
        ...checkDomain(['react', 'typescript', 'javascript', 'frontend', 'websockets', 'css', 'html', 'next.js']),
      },
    ];
  }, [canonicalSkills, structuredProjects, structuredExperiences, resume]);

  // Handle Resume Replacement
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsReplacingResume(true);
    setResumeActionError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const uploaded = await api.upload<ParsedResumeData>('/api/resumes/upload', formData);
      setResume(uploaded);

      // Trigger parse & vectorization
      try {
        const parsed = await api.post<ParsedResumeData>(`/api/resumes/${uploaded.id}/parse`);
        setResume(parsed);
      } catch (parseErr) {
        console.warn('Parsing triggered with notice:', parseErr);
        setResume(uploaded);
      }

      await refreshUser();
      await fetchData();
    } catch (err) {
      console.error('Failed to replace resume:', err);
      setResumeActionError('Failed to replace resume. Please try again.');
    } finally {
      setIsReplacingResume(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleViewResume = async () => {
    if (isOpeningResume) return;

    setResumeActionError(null);
    setIsOpeningResume(true);

    const fileName = resume?.file_name || '';
    const fileNameLower = fileName.toLowerCase();
    const storedMime = (resume?.mime_type || '').toLowerCase();

    // Check if file is known to be a DOCX file
    const knownDocx =
      fileNameLower.endsWith('.docx') ||
      storedMime === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

    // For PDF / non-DOCX files: open popup immediately in the user gesture call stack
    // (NO noopener/noreferrer flags so browser retains window reference for location.href)
    let previewWindow: Window | null = null;
    if (!knownDocx) {
      previewWindow = window.open('about:blank', '_blank');
    }

    try {
      // Authenticated binary fetch of current resume file
      const blob = await api.getBlob('/api/v1/resumes/current/file');

      if (!blob || blob.size === 0) {
        throw new Error('Received empty resume file from server.');
      }

      const blobType = (blob.type || '').toLowerCase();

      // Branch behavior using a trusted combination of MIME and file extension
      const isPdf =
        blobType.includes('pdf') ||
        fileNameLower.endsWith('.pdf') ||
        storedMime === 'application/pdf';

      const isDocx =
        !isPdf &&
        (blobType.includes('wordprocessingml') ||
          blobType.includes('officedocument') ||
          blobType.includes('msword') ||
          fileNameLower.endsWith('.docx') ||
          storedMime.includes('word') ||
          knownDocx);

      const objectUrl = URL.createObjectURL(blob);

      if (isPdf) {
        // PDF: open inline in the preview window
        if (previewWindow && !previewWindow.closed) {
          previewWindow.location.href = objectUrl;
        } else {
          const fallbackWin = window.open(objectUrl, '_blank');
          if (!fallbackWin) {
            // Popup blocker triggered fallback: direct download
            const a = document.createElement('a');
            a.href = objectUrl;
            a.download = fileName || 'resume.pdf';
            document.body.appendChild(a);
            a.click();
            a.remove();
          }
        }
        // Retain object URL for 60 seconds so browser PDF reader has sufficient time to stream/render
        setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
      } else {
        // DOCX or non-PDF: close preview window if opened, and trigger download
        if (previewWindow && !previewWindow.closed) {
          previewWindow.close();
        }
        const a = document.createElement('a');
        a.href = objectUrl;
        a.download = fileName || (isDocx ? 'resume.docx' : 'resume');
        document.body.appendChild(a);
        a.click();
        a.remove();
        // Delay revoke after download click event loop
        setTimeout(() => URL.revokeObjectURL(objectUrl), 30000);
      }
    } catch (err: unknown) {
      if (previewWindow && !previewWindow.closed) {
        previewWindow.close();
      }
      console.error('Failed to view resume:', err);
      setResumeActionError('Resume could not be opened. Please try again.');
    } finally {
      setIsOpeningResume(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  // ---------------------------------------------------------------------------
  // Skeletons
  // ---------------------------------------------------------------------------
  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="w-full max-w-[1220px] mx-auto space-y-5 animate-pulse py-4">
          <div className="h-10 bg-slate-200/60 rounded-lg w-1/4" />
          <div className="h-28 bg-white border border-[#E2E2E2] rounded-xl" />
          <div className="h-16 bg-white border border-[#E2E2E2] rounded-xl" />
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            <div className="lg:col-span-8 h-96 bg-white border border-[#E2E2E2] rounded-xl" />
            <div className="lg:col-span-4 h-96 bg-white border border-[#E2E2E2] rounded-xl" />
          </div>
        </div>
      </DashboardLayout>
    );
  }

  const userInitial = getInitials(candidateName);
  const fullName = candidateName;
  const roleCount = preferences?.preferred_roles?.length || 0;
  const skillsCount = canonicalSkills.length;
  const projectCount = structuredProjects.length;

  return (
    <DashboardLayout>
      <div className="w-full max-w-[1220px] mx-auto space-y-4 sm:space-y-5 font-sans animate-fade-in pb-12">
        {/* ================================================== */}
        {/* 1. PAGE HEADER                                      */}
        {/* ================================================== */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
          <div>
            <span className="text-[10px] font-mono font-semibold tracking-wider text-[#6B6B6B] uppercase block">
              CAREER IDENTITY
            </span>
            <h1 className="font-serif text-2xl sm:text-3xl font-medium text-[#1B2A4A] tracking-tight">
              Profile
            </h1>
            <p className="text-xs sm:text-[13px] text-[#6B6B6B] mt-0.5 max-w-xl">
              The information Aptly uses to understand your career and personalize your opportunities.
            </p>
          </div>

          <button
            type="button"
            onClick={() => setIsDrawerOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#E2E2E2] bg-white hover:bg-[#F8FAFC] text-xs font-medium text-[#1A1A1A] transition-colors cursor-pointer shadow-2xs self-start sm:self-center"
          >
            <Pencil size={13} className="text-[#6B6B6B]" />
            <span>Edit profile</span>
          </button>
        </div>

        {/* ================================================== */}
        {/* 2. IDENTITY PANEL (Horizontal compact 90-110px)    */}
        {/* ================================================== */}
        <div className="bg-white border border-[#E2E2E2] rounded-xl p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-2xs">
          {/* Left: Avatar & Candidate Metadata */}
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-xl bg-[#1B2A4A] text-white flex items-center justify-center font-serif text-base font-bold shrink-0 overflow-hidden shadow-2xs">
              {user?.profile_picture_url && !avatarError ? (
                <img
                  src={user.profile_picture_url}
                  alt=""
                  onError={() => setAvatarError(true)}
                  className="w-full h-full object-cover"
                />
              ) : (
                <span>{userInitial}</span>
              )}
            </div>

            <div>
              <div className="flex items-center gap-2">
                <span className="font-serif text-lg font-bold text-[#1B2A4A] leading-tight">
                  {fullName}
                </span>
                <span className="px-2 py-0.5 rounded bg-[#EEF4FC] text-[#2563EB] text-[9.5px] font-semibold tracking-wider uppercase">
                  ACTIVE CANDIDATE
                </span>
              </div>

              <p className="text-xs text-[#4A5568] mt-0.5">
                <span className="font-semibold text-[#1A1A1A]">{candidateRole}</span> &middot;{' '}
                {educationDisplay.institution} &middot; {educationDisplay.gradYear} &middot;{' '}
                {educationDisplay.location}
              </p>

              <p className="text-[11px] text-[#9CA3AF] mt-0.5">
                Profile last updated {formatRelativeTime((preferences as { updated_at?: string } | null)?.updated_at || resume?.created_at)}
              </p>
            </div>
          </div>

          {/* Right: Deterministic Profile Readiness & Circular Gauge */}
          <div className="flex items-center md:justify-end gap-3.5 pt-2 md:pt-0 border-t md:border-t-0 border-[#F0F0F0]">
            <div className="text-left md:text-right">
              <span className="text-[10px] font-mono font-semibold tracking-wider text-[#6B6B6B] uppercase block">
                PROFILE READINESS
              </span>
              <p className="text-xs font-semibold text-[#1A1A1A]">
                {readiness.completed}/{readiness.total} essentials complete
              </p>
              <p className="text-[10.5px] text-[#9CA3AF]">
                {readiness.hasResume ? 'Resume uploaded' : 'Resume needed'} &middot;{' '}
                {readiness.hasRoles ? 'Targets set' : 'Targets needed'} &middot;{' '}
                {readiness.hasOpportunity ? 'Work mode ready' : 'Work mode needed'}
              </p>
            </div>

            {/* Circular Progress Indicator */}
            <div className="relative w-11 h-11 shrink-0 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path
                  className="text-[#E2E8F0]"
                  strokeWidth="3.2"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <path
                  className="text-[#1B2A4A] transition-all duration-700 ease-out"
                  strokeDasharray={`${readiness.percentage}, 100`}
                  strokeWidth="3.2"
                  strokeLinecap="round"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
              </svg>
              <span className="absolute text-[10px] font-bold text-[#1B2A4A] font-mono">
                {readiness.percentage}%
              </span>
            </div>
          </div>
        </div>

        {/* ================================================== */}
        {/* 3. CAREER SIGNAL STRIP (Continuous 4-cell row)     */}
        {/* ================================================== */}
        <div className="bg-white border border-[#E2E2E2] rounded-xl grid grid-cols-2 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-[#E2E2E2] shadow-2xs">
          {/* Cell 1: Target Roles */}
          <div className="p-3.5 sm:p-4">
            <span className="text-[10px] font-mono font-semibold tracking-wider text-[#6B6B6B] uppercase block">
              TARGET ROLES
            </span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-lg sm:text-xl font-bold text-[#1B2A4A] font-serif">
                {roleCount}
              </span>
              <span className="text-xs text-[#4A5568] truncate">
                {roleCount > 0
                  ? `${preferences?.preferred_roles[0]}${roleCount > 1 ? ` +${roleCount - 1}` : ''}`
                  : 'Configure roles'}
              </span>
            </div>
          </div>

          {/* Cell 2: Core Skills */}
          <div className="p-3.5 sm:p-4">
            <span className="text-[10px] font-mono font-semibold tracking-wider text-[#6B6B6B] uppercase block">
              CORE SKILLS
            </span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-lg sm:text-xl font-bold text-[#1B2A4A] font-serif">
                {skillsCount}
              </span>
              <span className="text-xs text-[#4A5568] truncate">
                {skillsCount > 0
                  ? `${canonicalSkills.slice(0, 3).join(' · ')}${skillsCount > 3 ? ` +${skillsCount - 3}` : ''}`
                  : 'Connect resume'}
              </span>
            </div>
          </div>

          {/* Cell 3: Projects */}
          <div className="p-3.5 sm:p-4">
            <span className="text-[10px] font-mono font-semibold tracking-wider text-[#6B6B6B] uppercase block">
              PROJECTS
            </span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-lg sm:text-xl font-bold text-[#1B2A4A] font-serif">
                {projectCount}
              </span>
              <span className="text-xs text-[#4A5568] truncate">
                {projectCount > 0 ? `${projectCount} verified projects` : 'No projects'}
              </span>
            </div>
          </div>

          {/* Cell 4: Resume */}
          <div className="p-3.5 sm:p-4">
            <span className="text-[10px] font-mono font-semibold tracking-wider text-[#6B6B6B] uppercase block">
              RESUME
            </span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-xs font-bold text-[#1B2A4A]">Current</span>
              <span className="text-xs text-[#4A5568] truncate">
                Updated {formatRelativeTime(resume?.created_at)} &middot; Indexed
              </span>
            </div>
          </div>
        </div>

        {/* ================================================== */}
        {/* 4. MAIN TWO-COLUMN GRID (67% / 33%)                */}
        {/* ================================================== */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          {/* ------------------------------------------------ */}
          {/* LEFT COLUMN: 67% (lg:col-span-8)                 */}
          {/* ------------------------------------------------ */}
          <div className="lg:col-span-8 space-y-5">
            {/* SECTION: Career Direction */}
            <div className="bg-white border border-[#E2E2E2] rounded-xl p-5 shadow-2xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#F0F0F0]">
                <div>
                  <h3 className="font-serif text-base font-bold text-[#1B2A4A]">Career Direction</h3>
                  <p className="text-xs text-[#6B6B6B]">What you&apos;re looking for next</p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsDrawerOpen(true)}
                  className="text-xs text-[#3D5580] hover:text-[#1B2A4A] hover:underline font-medium cursor-pointer"
                >
                  Edit
                </button>
              </div>

              <div className="space-y-3.5 text-xs">
                {/* Target Roles */}
                <div>
                  <span className="text-[10px] font-mono font-semibold text-[#6B6B6B] tracking-wider uppercase block mb-1.5">
                    TARGET ROLES
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {roleCount > 0 ? (
                      preferences?.preferred_roles.map((role) => (
                        <span
                          key={role}
                          className="px-2.5 py-1 rounded-md bg-[#F4F6F9] border border-[#E2E8F0] text-xs text-[#1A1A1A] font-medium"
                        >
                          {role}
                        </span>
                      ))
                    ) : (
                      <span className="text-slate-400 italic">None configured yet.</span>
                    )}
                  </div>
                </div>

                <div className="h-px bg-[#F5F5F5]" />

                {/* Opportunity Type */}
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-semibold text-[#6B6B6B] tracking-wider uppercase">
                    OPPORTUNITY TYPE
                  </span>
                  <span className="font-medium text-[#1A1A1A]">
                    {preferences?.opportunity_type === 'internship'
                      ? 'Internship'
                      : preferences?.opportunity_type === 'both'
                      ? 'Full-time, Internship'
                      : 'Full-time'}
                  </span>
                </div>

                <div className="h-px bg-[#F5F5F5]" />

                {/* Work Mode */}
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-semibold text-[#6B6B6B] tracking-wider uppercase">
                    WORK MODE
                  </span>
                  <span className="font-medium text-[#1A1A1A]">
                    {preferences?.user_type === 'remote'
                      ? 'Remote'
                      : preferences?.user_type === 'onsite'
                      ? 'On-site'
                      : 'Hybrid, Remote'}
                  </span>
                </div>

                <div className="h-px bg-[#F5F5F5]" />

                {/* Preferred Location */}
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-semibold text-[#6B6B6B] tracking-wider uppercase">
                    PREFERRED LOCATION
                  </span>
                  <span className="font-medium text-[#1A1A1A]">
                    {preferences?.preferred_location || 'Bengaluru, India'}
                  </span>
                </div>

                <div className="h-px bg-[#F5F5F5]" />

                {/* Interests */}
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-semibold text-[#6B6B6B] tracking-wider uppercase">
                    INTERESTS
                  </span>
                  <span className="font-medium text-[#1A1A1A] text-right max-w-xs truncate">
                    {preferences?.interests && preferences.interests.length > 0
                      ? preferences.interests.join(', ')
                      : 'Distributed Systems, API Architecture'}
                  </span>
                </div>
              </div>
            </div>

            {/* SECTION: Verified Skills */}
            <div className="bg-white border border-[#E2E2E2] rounded-xl p-5 shadow-2xs space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#F0F0F0]">
                <div>
                  <h3 className="font-serif text-base font-bold text-[#1B2A4A]">Verified Skills</h3>
                  <p className="text-xs text-[#6B6B6B]">Capabilities Aptly found in your current resume</p>
                </div>
                <span className="px-2 py-0.5 rounded border border-[#E2E2E2] bg-[#F8FAFC] text-[11px] font-mono text-[#4A5568]">
                  {skillsCount} verified
                </span>
              </div>

              {skillsCount === 0 ? (
                <p className="text-xs text-[#6B6B6B] italic py-2">
                  Connect a resume to build your verified skill profile.
                </p>
              ) : (
                <div className="space-y-3.5">
                  {skillGroups.map((group) => (
                    <div key={group.key}>
                      <span className="text-[10px] font-mono font-semibold text-[#6B6B6B] tracking-wider uppercase block mb-1.5">
                        {group.title}
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {group.skills.map((sk) => (
                          <span
                            key={sk}
                            className="px-2.5 py-1 rounded-md border border-[#E2E8F0] bg-white text-xs text-[#1A1A1A] font-normal shadow-2xs"
                          >
                            {sk}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* SECTION: Career Capability Map */}
            <div className="bg-white border border-[#E2E2E2] rounded-xl p-5 shadow-2xs space-y-4">
              <div className="flex items-start justify-between pb-3 border-b border-[#F0F0F0]">
                <div>
                  <h3 className="font-mono text-xs font-bold text-[#1B2A4A] tracking-wider uppercase">
                    CAREER CAPABILITY MAP
                  </h3>
                  <p className="text-xs text-[#6B6B6B] mt-0.5">
                    Empirical evidence weighting derived from projects, experience, and codebase artifacts
                  </p>
                </div>
                <span className="text-[10px] font-mono text-[#9CA3AF] tracking-wider uppercase shrink-0 pt-0.5">
                  Ledger v2.4
                </span>
              </div>

              <div className="space-y-4 pt-1">
                {capabilityMap.map((cap) => (
                  <div key={cap.name} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-[#1A1A1A]">{cap.name}</span>
                      <span className="text-[#4A5568] text-[11px] font-medium">{cap.label}</span>
                    </div>
                    <div className="w-full h-1 bg-[#EEF2F6] rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${cap.color} transition-all duration-500`}
                        style={{ width: cap.width }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* SECTION: Evidence from your resume */}
            <div className="bg-white border border-[#E2E2E2] rounded-xl p-5 shadow-2xs space-y-5">
              <div className="flex items-center justify-between pb-3 border-b border-[#F0F0F0]">
                <h3 className="font-serif text-base font-bold text-[#1B2A4A]">
                  Evidence from your resume
                </h3>
                <button
                  type="button"
                  onClick={handleViewResume}
                  disabled={isOpeningResume}
                  className="inline-flex items-center gap-1 text-xs text-[#3D5580] hover:text-[#1B2A4A] hover:underline font-medium cursor-pointer disabled:opacity-60"
                >
                  <span>{isOpeningResume ? 'Opening...' : 'View full resume'}</span>
                  <ArrowRight size={12} className={isOpeningResume ? 'animate-pulse' : ''} />
                </button>
              </div>

              {/* EXPERIENCE BLOCK */}
              {structuredExperiences.length > 0 && (
                <div className="space-y-3">
                  <span className="text-[10px] font-mono font-semibold text-[#6B6B6B] tracking-wider uppercase block">
                    EXPERIENCE
                  </span>
                  {structuredExperiences.map((exp, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-lg border border-[#E2E8F0] bg-[#FAFAFA] space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-xs text-[#1B2A4A]">{exp.company}</span>
                        <span className="text-[11px] text-[#6B6B6B] font-mono">{exp.dates}</span>
                      </div>
                      <p className="text-xs text-[#4A5568] font-medium">
                        {exp.role}{exp.location ? ` · ${exp.location}` : ''}
                      </p>
                      {exp.bullets.length > 0 && (
                        <ul className="space-y-1 text-xs text-[#475569] leading-relaxed pt-1">
                          {exp.bullets.map((b, bIdx) => (
                            <li key={bIdx} className="flex items-start gap-1.5">
                              <span className="text-[#94A3B8] shrink-0">•</span>
                              <span>{cleanExtractedText(b)}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* PROJECTS BLOCK (ONE parent card per project, bullets stay under project) */}
              <div className="space-y-3">
                <span className="text-[10px] font-mono font-semibold text-[#6B6B6B] tracking-wider uppercase block">
                  PROJECTS
                </span>

                {structuredProjects.length === 0 ? (
                  <p className="text-xs text-[#6B6B6B] italic">No resume evidence available yet.</p>
                ) : (
                  structuredProjects.map((proj, pIdx) => (
                    <div
                      key={pIdx}
                      className="p-4 rounded-lg border border-[#E2E8F0] bg-white space-y-2 shadow-2xs"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="font-semibold text-xs text-[#1B2A4A] leading-tight">
                          {proj.title}
                        </h4>
                        <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-medium shrink-0">
                          Verified
                        </span>
                      </div>

                      {/* Tech Stack Chips */}
                      {proj.technologies.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {proj.technologies.map((t, tIdx) => (
                            <span
                              key={tIdx}
                              className="px-2 py-0.5 rounded bg-[#F1F5F9] text-[#475569] text-[10.5px] font-mono"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Project Bullets strictly under parent project */}
                      {proj.bullets.length > 0 && (
                        <ul className="space-y-1 text-xs text-[#475569] leading-relaxed pt-1">
                          {proj.bullets.map((b, bIdx) => (
                            <li key={bIdx} className="flex items-start gap-1.5">
                              <span className="text-[#94A3B8] shrink-0">•</span>
                              <span>{b}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* SECTION: Strengthen your profile Strip */}
            <div className="bg-[#FAFBFD] border border-[#E2E8F0] rounded-xl p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs">
              <div className="flex items-center gap-2.5">
                <Lightbulb size={16} className="text-[#3D5580] shrink-0" />
                <p className="text-xs text-[#334155] leading-snug">
                  {readiness.percentage < 100 ? (
                    <>
                      <strong className="font-semibold text-[#1B2A4A]">Strengthen your profile:</strong>{' '}
                      Add 1 more target location to expand matched opportunities.
                    </>
                  ) : (
                    <>
                      <strong className="font-semibold text-[#1B2A4A]">Profile ready:</strong> Aptly
                      has enough information to personalize your search.
                    </>
                  )}
                </p>
              </div>

              {readiness.percentage < 100 && (
                <button
                  type="button"
                  onClick={() => setIsDrawerOpen(true)}
                  className="px-2.5 py-1 rounded border border-[#CBD5E1] bg-white hover:bg-slate-50 text-[11.5px] font-medium text-[#1E293B] shrink-0 transition-colors cursor-pointer self-start sm:self-auto"
                >
                  Add location
                </button>
              )}
            </div>
          </div>

          {/* ------------------------------------------------ */}
          {/* RIGHT COLUMN: 33% (lg:col-span-4)                */}
          {/* ------------------------------------------------ */}
          <div className="lg:col-span-4 space-y-5">
            {/* SECTION: Current Resume */}
            <div className="bg-white border border-[#E2E2E2] rounded-xl p-4 sm:p-5 shadow-2xs space-y-3.5">
              <div className="flex items-center justify-between pb-2.5 border-b border-[#F0F0F0]">
                <h3 className="font-serif text-base font-bold text-[#1B2A4A]">Current Resume</h3>
                <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-700">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                  Ready &amp; Indexed
                </span>
              </div>

              {/* Document Row */}
              <div className="p-3 rounded-lg border border-[#E2E8F0] bg-[#FAFAFA] flex items-center gap-3">
                <FileText size={20} className="text-[#1B2A4A] shrink-0" />
                <div className="truncate">
                  <p className="font-semibold text-xs text-[#1A1A1A] truncate">
                    {resume?.file_name || 'Resume.pdf'}
                  </p>
                  <p className="text-[10.5px] text-[#6B6B6B] mt-0.5">
                    Parsed &amp; Indexed &middot; Updated {formatDisplayDate(resume?.created_at)}
                  </p>
                  {resume?.file_name?.toLowerCase().endsWith('.docx') && (
                    <p className="text-[10px] text-[#9CA3AF] mt-0.5">Downloads the original DOCX</p>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="space-y-2 pt-1">
                <button
                  type="button"
                  onClick={handleViewResume}
                  disabled={isOpeningResume || isReplacingResume || !resume?.id}
                  className="w-full inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-[#1B2A4A] hover:bg-[#142038] text-white text-xs font-semibold transition-colors cursor-pointer shadow-2xs disabled:opacity-70"
                >
                  <Eye size={13} className={isOpeningResume ? 'animate-pulse' : ''} />
                  <span>{isOpeningResume ? 'Opening...' : 'View resume'}</span>
                </button>

                {resumeActionError && (
                  <p className="text-[11px] text-red-600 text-center">{resumeActionError}</p>
                )}

                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isReplacingResume || isOpeningResume}
                  className="w-full inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg border border-[#E2E2E2] bg-white hover:bg-[#F8FAFC] text-xs font-medium text-[#1A1A1A] transition-colors cursor-pointer shadow-2xs disabled:opacity-60"
                >
                  <RefreshCw size={12} className={isReplacingResume ? 'animate-spin' : ''} />
                  <span>{isReplacingResume ? 'Uploading & Parsing...' : 'Replace resume'}</span>
                </button>

                {/* Hidden input for resume replacement */}
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".pdf,.docx"
                  className="hidden"
                />
              </div>
            </div>

            {/* SECTION: Search Preferences */}
            <div className="bg-white border border-[#E2E2E2] rounded-xl p-4 sm:p-5 shadow-2xs space-y-3.5">
              <div className="flex items-center justify-between pb-2.5 border-b border-[#F0F0F0]">
                <h3 className="font-serif text-base font-bold text-[#1B2A4A]">Search Preferences</h3>
                <button
                  type="button"
                  onClick={() => setIsDrawerOpen(true)}
                  className="text-xs text-[#3D5580] hover:text-[#1B2A4A] hover:underline font-medium cursor-pointer"
                >
                  Edit
                </button>
              </div>

              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-[10px] font-mono font-semibold text-[#6B6B6B] tracking-wider uppercase block">
                    OPPORTUNITY
                  </span>
                  <p className="font-medium text-[#1A1A1A] mt-0.5">
                    {preferences?.opportunity_type === 'internship'
                      ? 'Internship / Full-time'
                      : preferences?.opportunity_type === 'both'
                      ? 'Full-time / Internship'
                      : 'Full-time'}
                  </p>
                </div>

                <div className="h-px bg-[#F5F5F5]" />

                <div>
                  <span className="text-[10px] font-mono font-semibold text-[#6B6B6B] tracking-wider uppercase block">
                    WORK MODE
                  </span>
                  <p className="font-medium text-[#1A1A1A] mt-0.5">
                    {preferences?.user_type === 'remote' ? 'Remote' : 'Hybrid / Remote'}
                  </p>
                </div>

                <div className="h-px bg-[#F5F5F5]" />

                <div>
                  <span className="text-[10px] font-mono font-semibold text-[#6B6B6B] tracking-wider uppercase block">
                    UPDATE FREQUENCY
                  </span>
                  <p className="font-medium text-[#1A1A1A] mt-0.5">
                    {personalization?.update_frequency === 'weekly'
                      ? 'Weekly summary'
                      : personalization?.update_frequency === 'important_only'
                      ? 'Important matches only'
                      : 'Daily briefing (08:00 IST)'}
                  </p>
                </div>

                <div className="h-px bg-[#F5F5F5]" />

                <div>
                  <span className="text-[10px] font-mono font-semibold text-[#6B6B6B] tracking-wider uppercase block">
                    MATCH FOCUS
                  </span>
                  <p className="font-medium text-[#1A1A1A] mt-0.5">
                    High tech overlap &amp; compensation
                  </p>
                </div>
              </div>
            </div>

            {/* SECTION: Account */}
            <div className="bg-white border border-[#E2E2E2] rounded-xl p-4 sm:p-5 shadow-2xs space-y-3.5">
              <div className="pb-2.5 border-b border-[#F0F0F0]">
                <h3 className="font-serif text-base font-bold text-[#1B2A4A]">Account</h3>
              </div>

              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-[10px] font-mono font-semibold text-[#6B6B6B] tracking-wider uppercase block">
                    EMAIL
                  </span>
                  <p className="font-mono text-[#1A1A1A] text-[11.5px] truncate mt-0.5">
                    {user?.email || 'user@example.com'}
                  </p>
                </div>

                <div className="h-px bg-[#F5F5F5]" />

                <div>
                  <span className="text-[10px] font-mono font-semibold text-[#6B6B6B] tracking-wider uppercase block">
                    SIGN-IN METHOD
                  </span>
                  <p className="font-medium text-[#1A1A1A] mt-0.5">Google Sign-In (OAuth2)</p>
                </div>

                <div className="h-px bg-[#F5F5F5]" />

                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-[10px] font-mono font-semibold text-[#6B6B6B] tracking-wider uppercase block">
                      ACCOUNT STATUS
                    </span>
                    <p className="font-medium text-[#1A1A1A] mt-0.5">Active</p>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-[#F1F5F9] text-[#475569] text-[10px] font-mono">
                    Standard
                  </span>
                </div>

                {/* Sign Out */}
                <div className="pt-2 border-t border-[#F0F0F0]">
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="w-full flex items-center justify-between text-red-600 hover:text-red-700 text-xs font-medium cursor-pointer transition-colors pt-1"
                  >
                    <span>Sign out</span>
                    <LogOut size={13} />
                  </button>
                </div>
              </div>
            </div>

            {/* Micro footer */}
            <div className="flex items-center justify-between text-[10px] text-[#9CA3AF] font-mono px-1">
              <span>Aptly Workspace v1.12</span>
              <span>Security ID - {user?.id ? String(user.id).slice(0, 4) : '9942'}</span>
            </div>
          </div>
        </div>

        {/* Edit Profile Drawer */}
        <EditProfileDrawer
          isOpen={isDrawerOpen}
          onClose={() => setIsDrawerOpen(false)}
          preferences={preferences}
          personalization={personalization}
          onSaved={() => {
            fetchData();
            refreshUser();
          }}
        />
      </div>
    </DashboardLayout>
  );
}

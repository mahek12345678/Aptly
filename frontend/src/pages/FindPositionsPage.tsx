import { useEffect, useState, useMemo, useCallback } from 'react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import {
  Search,
  RefreshCw,
  AlertCircle,
  ArrowLeft,
  ChevronDown,
} from 'lucide-react';
import { api } from '@/lib/api';
import {
  JobMatchItem,
  JobMatchesListResponse,
  RefreshMatchesResponse,
  TaskStatusResponse,
  ToggleSaveResponse,
} from '@/types/jobs';
import { JobLedgerRow } from '@/components/jobs/JobLedgerRow';
import { JobIntelligencePane } from '@/components/jobs/JobIntelligencePane';

export default function FindPositionsPage() {
  const [matches, setMatches] = useState<JobMatchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState<
    'all' | 'saved' | 'remote' | 'hybrid' | 'internship' | 'full_time'
  >('all');
  const [sortBy, setSortBy] = useState<'best_match' | 'newest' | 'recently_posted'>('best_match');

  // Currently selected match
  const [selectedMatchId, setSelectedMatchId] = useState<string | null>(null);

  // Mobile detail view toggle
  const [mobileDetailOpen, setMobileDetailOpen] = useState(false);

  // Fetch matches from API
  const fetchMatches = useCallback(async (showFullLoader = true) => {
    if (showFullLoader) setLoading(true);
    setError(null);
    try {
      const response = await api.get<JobMatchesListResponse>('/api/v1/jobs/matches?limit=60');
      const items = response.items || [];
      setMatches(items);
      setLastRefreshedAt(response.last_refreshed_at);

      // Auto-select top match if nothing is selected or previous selection no longer exists
      if (items.length > 0) {
        setSelectedMatchId((prev) => {
          if (prev && items.some((item) => item.id === prev)) {
            return prev;
          }
          return items[0].id;
        });
      }
    } catch (err: any) {
      console.error('Failed to load matches:', err);
      setError(err?.message || 'Unable to load personalized matches at this time.');
    } finally {
      if (showFullLoader) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMatches();
  }, [fetchMatches]);

  // Handle Refresh Action
  const handleRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      const res = await api.post<RefreshMatchesResponse>('/api/v1/jobs/matches/refresh');
      // If task queued, poll task status
      if (res.task_id && res.status === 'queued') {
        const taskId = res.task_id;
        const pollInterval = 1200;
        const maxAttempts = 35;
        let attempts = 0;
        while (attempts < maxAttempts) {
          await new Promise((resolve) => setTimeout(resolve, pollInterval));
          attempts++;
          try {
            const taskStatus = await api.get<TaskStatusResponse>(`/api/v1/jobs/matches/tasks/${taskId}`);
            if (taskStatus.ready) break;
          } catch (pollErr) {
            console.warn('Task status poll error:', pollErr);
            break;
          }
        }
      }
      await fetchMatches(false);
      if (res.refreshed_at) {
        setLastRefreshedAt(res.refreshed_at);
      }
    } catch (err: any) {
      console.error('Refresh error:', err);
      setError('We couldn\'t refresh opportunities right now. Your previous matches are still available.');
    } finally {
      setRefreshing(false);
    }
  };

  // Toggle Save / Bookmark
  const handleToggleSave = async (matchId: string) => {
    // Optimistic UI update
    setMatches((prev) =>
      prev.map((m) => (m.id === matchId ? { ...m, saved: !m.saved } : m))
    );

    try {
      const res = await api.post<ToggleSaveResponse>(`/api/v1/jobs/matches/${matchId}/save`);
      setMatches((prev) =>
        prev.map((m) => (m.id === matchId ? { ...m, saved: res.saved } : m))
      );
    } catch (err) {
      console.error('Save toggle failed:', err);
      // Revert optimistic update
      setMatches((prev) =>
        prev.map((m) => (m.id === matchId ? { ...m, saved: !m.saved } : m))
      );
    }
  };

  // Saved count
  const savedCount = useMemo(() => matches.filter((m) => m.saved).length, [matches]);

  // Filtered and Strictly Sorted Listings
  const filteredAndSortedMatches = useMemo(() => {
    let result = matches.filter((item) => {
      // 1. Filter by category
      if (activeFilter === 'saved' && !item.saved) return false;
      if (activeFilter === 'remote') {
        const loc = (item.job.location || '').toLowerCase();
        const emp = (item.job.employment_type || '').toLowerCase();
        if (!loc.includes('remote') && !emp.includes('remote')) return false;
      }
      if (activeFilter === 'hybrid') {
        const loc = (item.job.location || '').toLowerCase();
        if (!loc.includes('hybrid')) return false;
      }
      if (activeFilter === 'full_time') {
        const emp = (item.job.employment_type || '').toLowerCase();
        if (!emp.includes('full')) return false;
      }
      if (activeFilter === 'internship') {
        const emp = (item.job.employment_type || '').toLowerCase();
        if (!emp.includes('intern')) return false;
      }

      // 2. Search query matching
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const role = item.job.role_title.toLowerCase();
        const company = item.job.company.toLowerCase();
        const desc = item.job.description.toLowerCase();
        const loc = (item.job.location || '').toLowerCase();
        if (!role.includes(q) && !company.includes(q) && !desc.includes(q) && !loc.includes(q)) {
          return false;
        }
      }

      return true;
    });

    // 3. Strict Sorting (Fixes the Ranking Inconsistency Bug!)
    if (sortBy === 'best_match') {
      result = [...result].sort((a, b) => b.final_score - a.final_score);
    } else if (sortBy === 'newest' || sortBy === 'recently_posted') {
      result = [...result].sort((a, b) => {
        const timeA = new Date(a.job.posted_at || a.matched_at).getTime();
        const timeB = new Date(b.job.posted_at || b.matched_at).getTime();
        return timeB - timeA;
      });
    }

    return result;
  }, [matches, activeFilter, searchQuery, sortBy]);

  // Selected Match Object
  const selectedMatch = useMemo(() => {
    if (!selectedMatchId && filteredAndSortedMatches.length > 0) {
      return filteredAndSortedMatches[0];
    }
    return (
      filteredAndSortedMatches.find((m) => m.id === selectedMatchId) ||
      filteredAndSortedMatches[0] ||
      null
    );
  }, [filteredAndSortedMatches, selectedMatchId]);

  // Selected Match Rank index within current sorted view
  const selectedRank = useMemo(() => {
    if (!selectedMatch) return 1;
    const idx = filteredAndSortedMatches.findIndex((m) => m.id === selectedMatch.id);
    return idx >= 0 ? idx + 1 : 1;
  }, [filteredAndSortedMatches, selectedMatch]);

  // Format relative time for header
  const formatRelativeTime = (isoString?: string | null) => {
    if (!isoString) return '10m ago';
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return 'recently';
    const diffMin = Math.floor((Date.now() - date.getTime()) / 60000);
    if (diffMin < 1) return 'just now';
    if (diffMin === 1) return '1m ago';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours === 1) return '1h ago';
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
  };

  return (
    <DashboardLayout>
      <div className="space-y-4 max-w-[1360px] mx-auto pb-8 animate-in fade-in-50 duration-200">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="font-serif text-2xl sm:text-3xl font-bold text-[#1A1A1A] tracking-tight">
              Find New Positions
            </h1>
            <p className="text-xs sm:text-sm text-[#6B6B6B] mt-0.5">
              Fresh opportunities ranked for your profile.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-[#6B6B6B] font-mono">
              {refreshing
                ? 'Refreshing matches...'
                : `Updated ${formatRelativeTime(lastRefreshedAt)}`}
            </span>

            <button
              type="button"
              disabled={refreshing}
              onClick={handleRefresh}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#E2E2E2] bg-white text-[#1A1A1A] text-xs font-semibold hover:bg-slate-50 transition-colors cursor-pointer disabled:opacity-50"
            >
              <RefreshCw
                size={13}
                className={refreshing ? 'animate-spin text-[#1B2A4A]' : 'text-[#6B6B6B]'}
              />
              <span>{refreshing ? 'Refreshing matches...' : 'Refresh matches'}</span>
            </button>
          </div>
        </div>

        {/* Search & Filter Toolbar */}
        <div className="bg-white rounded-xl border border-[#E2E2E2] p-2.5 sm:px-3 sm:py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs">
          {/* Search Box */}
          <div className="relative flex-1 min-w-[240px] max-w-md">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search roles, companies, skills..."
              className="w-full pl-8.5 pr-8 py-1.5 rounded-lg bg-[#FAFAFA] border border-[#E2E2E2] text-xs text-[#1A1A1A] placeholder:text-[#9CA3AF] focus:outline-none focus:border-[#1B2A4A] transition-all"
            />
            <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] font-mono text-[#9CA3AF] border border-[#E2E2E2] px-1 rounded bg-white">
              ⌘K
            </span>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-1 flex-wrap">
            <button
              type="button"
              onClick={() => setActiveFilter('all')}
              className={`px-3 py-1.5 rounded-lg font-medium text-xs transition-colors cursor-pointer ${
                activeFilter === 'all'
                  ? 'bg-[#1B2A4A] text-white'
                  : 'text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-slate-50'
              }`}
            >
              All
            </button>

            <button
              type="button"
              onClick={() => setActiveFilter('saved')}
              className={`px-3 py-1.5 rounded-lg font-medium text-xs transition-colors cursor-pointer ${
                activeFilter === 'saved'
                  ? 'bg-[#1B2A4A] text-white'
                  : 'text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-slate-50'
              }`}
            >
              Saved {savedCount > 0 ? `(${savedCount})` : ''}
            </button>

            <button
              type="button"
              onClick={() => setActiveFilter('remote')}
              className={`px-3 py-1.5 rounded-lg font-medium text-xs transition-colors cursor-pointer ${
                activeFilter === 'remote'
                  ? 'bg-[#1B2A4A] text-white'
                  : 'text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-slate-50'
              }`}
            >
              Remote
            </button>

            <button
              type="button"
              onClick={() => setActiveFilter('hybrid')}
              className={`px-3 py-1.5 rounded-lg font-medium text-xs transition-colors cursor-pointer ${
                activeFilter === 'hybrid'
                  ? 'bg-[#1B2A4A] text-white'
                  : 'text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-slate-50'
              }`}
            >
              Hybrid
            </button>

            <button
              type="button"
              onClick={() => setActiveFilter('internship')}
              className={`px-3 py-1.5 rounded-lg font-medium text-xs transition-colors cursor-pointer ${
                activeFilter === 'internship'
                  ? 'bg-[#1B2A4A] text-white'
                  : 'text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-slate-50'
              }`}
            >
              Internship
            </button>

            <button
              type="button"
              onClick={() => setActiveFilter('full_time')}
              className={`px-3 py-1.5 rounded-lg font-medium text-xs transition-colors cursor-pointer ${
                activeFilter === 'full_time'
                  ? 'bg-[#1B2A4A] text-white'
                  : 'text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-slate-50'
              }`}
            >
              Full-time
            </button>
          </div>

          {/* Sort Dropdown */}
          <div className="flex items-center gap-1.5 text-xs text-[#6B6B6B]">
            <span>Sort:</span>
            <div className="relative">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                aria-label="Sort opportunities"
                className="appearance-none pl-2.5 pr-6 py-1 rounded-lg border border-[#E2E2E2] bg-[#FAFAFA] text-xs font-semibold text-[#1A1A1A] focus:outline-none focus:border-[#1B2A4A] cursor-pointer"
              >
                <option value="best_match">Best match</option>
                <option value="newest">Newest</option>
                <option value="recently_posted">Recently posted</option>
              </select>
              <ChevronDown
                size={12}
                className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-[#6B6B6B]"
              />
            </div>
          </div>
        </div>

        {/* Error Alert (Gracefully preserves existing matches) */}
        {error && (
          <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center justify-between gap-3 animate-in fade-in duration-150">
            <div className="flex items-center gap-2">
              <AlertCircle size={15} className="text-amber-700 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={handleRefresh}
              className="font-semibold underline hover:text-amber-950 cursor-pointer"
            >
              Try again
            </button>
          </div>
        )}

        {/* Main Split-Pane Container */}
        {loading ? (
          /* Structured Skeleton Matching the Split-Pane Layout */
          <div className="border border-[#E2E2E2] rounded-xl bg-white overflow-hidden flex flex-col md:flex-row h-[calc(100vh-210px)] min-h-[620px] animate-pulse">
            {/* Left Skeleton Column */}
            <div className="w-full md:w-[420px] lg:w-[450px] shrink-0 border-r border-[#E2E2E2] p-4 space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="p-3 border-b border-slate-100 space-y-2">
                  <div className="flex justify-between">
                    <div className="w-24 h-4 bg-slate-200 rounded" />
                    <div className="w-16 h-4 bg-slate-200 rounded" />
                  </div>
                  <div className="w-48 h-4 bg-slate-200 rounded" />
                  <div className="w-32 h-3 bg-slate-100 rounded" />
                </div>
              ))}
            </div>

            {/* Right Skeleton Column */}
            <div className="flex-1 p-6 space-y-6">
              <div className="flex justify-between items-start">
                <div className="space-y-2">
                  <div className="w-32 h-4 bg-slate-200 rounded" />
                  <div className="w-64 h-6 bg-slate-200 rounded" />
                  <div className="w-44 h-3 bg-slate-100 rounded" />
                </div>
                <div className="w-24 h-14 bg-slate-200 rounded-xl" />
              </div>
              <div className="h-24 bg-slate-100 rounded-xl" />
              <div className="h-32 bg-slate-100 rounded-xl" />
            </div>
          </div>
        ) : filteredAndSortedMatches.length > 0 ? (
          /* Split-Pane: Left Ranked Ledger + Right Intelligence View */
          <div className="border border-[#E2E2E2] rounded-xl bg-white overflow-hidden flex flex-col md:flex-row h-[calc(100vh-210px)] min-h-[620px] shadow-2xs">
            {/* Left Column: Ranked Opportunities Ledger */}
            <div
              className={`w-full md:w-[420px] lg:w-[450px] shrink-0 border-r border-[#E2E2E2] flex flex-col h-full bg-white ${
                mobileDetailOpen ? 'hidden md:flex' : 'flex'
              }`}
            >
              {/* Scrollable Rows */}
              <div className="flex-1 overflow-y-auto divide-y divide-[#E2E2E2]">
                {filteredAndSortedMatches.map((match, idx) => (
                  <JobLedgerRow
                    key={match.id}
                    match={match}
                    rank={idx + 1}
                    isSelected={selectedMatch?.id === match.id}
                    onSelect={(m) => {
                      setSelectedMatchId(m.id);
                      setMobileDetailOpen(true);
                    }}
                  />
                ))}
              </div>

              {/* Status Footer */}
              <div className="py-2.5 px-4 border-t border-[#E2E2E2] text-center text-[11px] font-mono text-[#6B6B6B] bg-[#FAFAFA]">
                Showing {filteredAndSortedMatches.length} of {matches.length} Calibrated Roles
              </div>
            </div>

            {/* Right Column: Selected-Job Intelligence Pane */}
            <div
              className={`flex-1 flex flex-col h-full bg-white ${
                mobileDetailOpen ? 'flex' : 'hidden md:flex'
              }`}
            >
              {/* Mobile Back Button */}
              {mobileDetailOpen && (
                <div className="md:hidden p-3 border-b border-[#E2E2E2] bg-[#FAFAFA] flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setMobileDetailOpen(false)}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#1B2A4A] hover:underline cursor-pointer"
                  >
                    <ArrowLeft size={14} />
                    <span>Back to opportunities</span>
                  </button>
                </div>
              )}

              <JobIntelligencePane
                match={selectedMatch}
                rank={selectedRank}
                onToggleSave={handleToggleSave}
              />
            </div>
          </div>
        ) : (
          /* Empty State */
          <div className="border border-[#E2E2E2] rounded-xl bg-white p-12 text-center shadow-2xs space-y-3">
            <h3 className="font-serif text-xl font-bold text-[#1A1A1A]">
              No matches yet.
            </h3>
            <p className="text-xs sm:text-sm text-[#6B6B6B] max-w-md mx-auto leading-relaxed">
              Complete your profile and resume so Aptly can rank opportunities for you.
            </p>
            <div className="pt-2">
              <button
                type="button"
                onClick={handleRefresh}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#1B2A4A] text-white text-xs font-semibold hover:bg-[#142038] transition-colors cursor-pointer"
              >
                <RefreshCw size={13} />
                <span>Refresh matches</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}

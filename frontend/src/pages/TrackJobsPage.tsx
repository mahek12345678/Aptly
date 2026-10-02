import { useState, useEffect, useMemo, useCallback } from 'react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import {
  Plus,
  Search,
  Filter,
  ArrowUpDown,
  Briefcase,
  RefreshCw,
  Clock,
  ExternalLink,
  Check,
  Trash2,
} from 'lucide-react';
import { api } from '@/lib/api';
import {
  ApplicationStatus,
  CreateApplicationPayload,
  JobApplication,
  KANBAN_STAGES,
  UpdateApplicationPayload,
} from '@/types/application';
import { KanbanBoard } from '@/components/kanban/KanbanBoard';
import { ApplicationModal } from '@/components/kanban/ApplicationModal';

export default function TrackJobsPage() {
  const [applications, setApplications] = useState<JobApplication[]>([]);
  const [pendingApplications, setPendingApplications] = useState<JobApplication[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'updated_at' | 'deadline'>('updated_at');

  // Header "Add application" modal state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // Fetch applications & pending in-progress applications
  const fetchApplications = useCallback(async () => {
    try {
      setError(null);
      const [kanbanData, pendingData] = await Promise.all([
        api.get<JobApplication[]>('/api/v1/applications'),
        api.get<JobApplication[]>('/api/v1/applications/pending'),
      ]);
      setApplications(kanbanData || []);
      setPendingApplications(pendingData || []);
    } catch (err: any) {
      setError(err?.message || 'Failed to load applications.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchApplications();

    // Listen to confirmation events from banner
    const handleConfirmed = () => {
      fetchApplications();
    };
    window.addEventListener('aptly:application-confirmed', handleConfirmed);
    window.addEventListener('aptly:apply-started', handleConfirmed);

    return () => {
      window.removeEventListener('aptly:application-confirmed', handleConfirmed);
      window.removeEventListener('aptly:apply-started', handleConfirmed);
    };
  }, [fetchApplications]);

  // Handle confirming a pending in-progress application
  const handleConfirmPending = async (appId: string) => {
    try {
      const confirmed = await api.post<JobApplication>(
        `/api/v1/applications/${appId}/confirm-applied`
      );
      setPendingApplications((prev) => prev.filter((a) => a.id !== appId));
      setApplications((prev) => [confirmed, ...prev]);
    } catch (err) {
      console.error('Failed to confirm pending application:', err);
    }
  };

  // Handle removing a pending in-progress application
  const handleRemovePending = async (appId: string) => {
    try {
      await api.delete(`/api/v1/applications/${appId}`);
      setPendingApplications((prev) => prev.filter((a) => a.id !== appId));
    } catch (err) {
      console.error('Failed to delete pending application:', err);
    }
  };

  // Handle resuming a pending external application
  const handleResumePending = (url?: string | null) => {
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  };

  // Move application (drag & drop PATCH)
  const handleMoveApplication = async (id: string, newStatus: ApplicationStatus) => {
    // Call backend PATCH
    await api.patch(`/api/v1/applications/${id}`, { status: newStatus });
    // Update local state without full reload
    setApplications((prev) =>
      prev.map((app) => (app.id === id ? { ...app, status: newStatus } : app))
    );
  };

  // Save application (Create or Update)
  const handleSaveApplication = async (
    payload: CreateApplicationPayload | UpdateApplicationPayload,
    id?: string
  ) => {
    if (id) {
      // Edit
      const updated = await api.patch<JobApplication>(`/api/v1/applications/${id}`, payload);
      setApplications((prev) =>
        prev.map((app) => (app.id === id ? updated : app))
      );
    } else {
      // Create
      const created = await api.post<JobApplication>('/api/v1/applications', payload);
      setApplications((prev) => [created, ...prev]);
    }
  };

  // Delete application
  const handleDeleteApplication = async (id: string) => {
    await api.delete(`/api/v1/applications/${id}`);
    setApplications((prev) => prev.filter((app) => app.id !== id));
  };

  // Filtered & sorted applications
  const filteredApplications = useMemo(() => {
    let result = [...applications];

    // Status filter
    if (selectedStatus !== 'all') {
      result = result.filter((app) => app.status === selectedStatus);
    }

    // Search query (company or role)
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (app) =>
          app.company.toLowerCase().includes(q) ||
          app.role.toLowerCase().includes(q)
      );
    }

    // Sorting
    result.sort((a, b) => {
      if (sortBy === 'deadline') {
        if (!a.deadline) return 1;
        if (!b.deadline) return -1;
        return new Date(a.deadline).getTime() - new Date(b.deadline).getTime();
      }
      // default: updated_at descending
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });

    return result;
  }, [applications, selectedStatus, searchQuery, sortBy]);

  const hasZeroApplications = applications.length === 0 && pendingApplications.length === 0 && !isLoading;
  const hasNoFilterResults = applications.length > 0 && filteredApplications.length === 0;

  return (
    <DashboardLayout>
      <div className="space-y-5 max-w-[1560px] mx-auto pb-10">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="font-serif text-2xl sm:text-3xl font-bold text-[#1B2A4A] tracking-tight">
              Track Jobs
            </h1>
            <p className="text-xs sm:text-sm text-[#6B6B6B] mt-1">
              Keep every application and next step in one place.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => setIsAddModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[#1B2A4A] hover:bg-[#142038] text-white text-xs sm:text-sm font-semibold transition-colors shadow-xs active:scale-[0.98]"
            >
              <Plus size={16} />
              <span>Add application</span>
            </button>
          </div>
        </div>

        {/* Applications in progress section (pending external applications) */}
        {pendingApplications.length > 0 && (
          <div className="rounded-2xl bg-white border border-[#E2E2E2] p-4 sm:p-5 shadow-2xs space-y-3 animate-in fade-in duration-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="p-1.5 rounded-lg bg-amber-50 text-amber-700 border border-amber-200">
                  <Clock size={16} />
                </span>
                <div>
                  <h3 className="font-serif text-sm sm:text-base font-bold text-[#1B2A4A]">
                    Applications in progress ({pendingApplications.length})
                  </h3>
                  <p className="text-xs text-[#6B6B6B]">
                    External applications you have opened. Confirm submission to move them into Kanban.
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-1">
              {pendingApplications.map((app) => (
                <div
                  key={app.id}
                  className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 flex flex-col justify-between gap-3 hover:border-slate-300 transition-colors"
                >
                  <div className="space-y-0.5">
                    <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                      {app.company}
                    </span>
                    <h4 className="font-serif text-sm font-bold text-[#1A1A1A] line-clamp-1">
                      {app.role}
                    </h4>
                  </div>

                  <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-200/60">
                    <button
                      type="button"
                      onClick={() => handleResumePending(app.application_url)}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-blue-700 hover:text-blue-900 transition-colors cursor-pointer"
                    >
                      <ExternalLink size={12} />
                      <span>Resume application</span>
                    </button>

                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => handleConfirmPending(app.id)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-[#1B2A4A] hover:bg-[#142038] text-white text-xs font-semibold shadow-2xs transition-colors cursor-pointer active:scale-95"
                      >
                        <Check size={12} />
                        <span>Mark as applied</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => handleRemovePending(app.id)}
                        title="Remove"
                        className="p-1 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-slate-200/60 transition-colors cursor-pointer"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Filter and Search Bar */}
        {!hasZeroApplications && applications.length > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-3 p-2.5 rounded-xl bg-white border border-[#E2E2E2] shadow-2xs">
            {/* Left: Search input */}
            <div className="relative flex-1 min-w-[200px] max-w-sm">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]"
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search company or role..."
                className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-[#E2E2E2] focus:border-[#1B2A4A] focus:outline-none bg-[#FAFAFA] text-[#1A1A1A] placeholder:text-[#9CA3AF]"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-[#9CA3AF] hover:text-[#1A1A1A]"
                >
                  ✕
                </button>
              )}
            </div>

            {/* Right: Stage Filter & Sort By */}
            <div className="flex items-center gap-2.5 flex-wrap">
              {/* Stage filter */}
              <div className="flex items-center gap-1.5 text-xs text-[#6B6B6B]">
                <Filter size={13} className="text-[#9CA3AF]" />
                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                  className="px-2 py-1.5 text-xs rounded-lg border border-[#E2E2E2] bg-white text-[#1A1A1A] focus:outline-none focus:border-[#1B2A4A]"
                >
                  <option value="all">All Stages ({applications.length})</option>
                  {KANBAN_STAGES.map((s) => {
                    const count = applications.filter((a) => a.status === s.id).length;
                    return (
                      <option key={s.id} value={s.id}>
                        {s.label} ({count})
                      </option>
                    );
                  })}
                </select>
              </div>

              {/* Sort By */}
              <div className="flex items-center gap-1.5 text-xs text-[#6B6B6B]">
                <ArrowUpDown size={13} className="text-[#9CA3AF]" />
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as 'updated_at' | 'deadline')}
                  className="px-2 py-1.5 text-xs rounded-lg border border-[#E2E2E2] bg-white text-[#1A1A1A] focus:outline-none focus:border-[#1B2A4A]"
                >
                  <option value="updated_at">Recently Updated</option>
                  <option value="deadline">Nearest Deadline</option>
                </select>
              </div>

              {(searchQuery || selectedStatus !== 'all') && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('');
                    setSelectedStatus('all');
                  }}
                  className="px-2.5 py-1.5 text-xs text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-[#F3F4F6] rounded-lg transition-colors font-medium"
                >
                  Reset
                </button>
              )}
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="h-64 flex flex-col items-center justify-center text-center p-8 bg-white rounded-xl border border-[#E2E2E2]">
            <RefreshCw size={24} className="text-[#3D5580] animate-spin mb-3" />
            <p className="text-xs text-[#6B6B6B]">Loading your applications...</p>
          </div>
        )}

        {/* Error State */}
        {!isLoading && error && (
          <div className="p-4 rounded-xl bg-[#FEF2F2] border border-[#FCA5A5] text-[#991B1B] text-xs flex items-center justify-between">
            <span>{error}</span>
            <button
              type="button"
              onClick={fetchApplications}
              className="text-xs font-semibold underline hover:no-underline ml-4"
            >
              Retry
            </button>
          </div>
        )}

        {/* Zero Applications Empty State */}
        {hasZeroApplications && (
          <div className="p-8 sm:p-14 rounded-2xl bg-white border border-[#E2E2E2] text-center max-w-xl mx-auto shadow-2xs">
            <div className="w-14 h-14 rounded-2xl bg-[#F0F4F8] text-[#1B2A4A] flex items-center justify-center mx-auto mb-4 border border-[#D5DEE8]">
              <Briefcase size={26} />
            </div>
            <h3 className="font-serif text-lg sm:text-xl font-bold text-[#1B2A4A] mb-1.5">
              No applications yet.
            </h3>
            <p className="text-xs sm:text-sm text-[#6B6B6B] leading-relaxed mb-6 max-w-sm mx-auto">
              Add your first application to start tracking your progress across interview stages.
            </p>
            <button
              type="button"
              onClick={() => setIsAddModalOpen(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#1B2A4A] hover:bg-[#142038] text-white text-xs sm:text-sm font-semibold transition-colors shadow-xs"
            >
              <Plus size={16} />
              <span>Add application</span>
            </button>
          </div>
        )}

        {/* Filtered empty state */}
        {hasNoFilterResults && (
          <div className="p-8 rounded-xl bg-white border border-[#E2E2E2] text-center max-w-md mx-auto">
            <p className="text-xs sm:text-sm text-[#1A1A1A] font-medium mb-1">
              No applications match your filter.
            </p>
            <p className="text-xs text-[#6B6B6B] mb-4">
              Try adjusting your search query or stage filter.
            </p>
            <button
              type="button"
              onClick={() => {
                setSearchQuery('');
                setSelectedStatus('all');
              }}
              className="px-3.5 py-1.5 rounded-lg bg-[#F3F4F6] hover:bg-[#E5E7EB] text-xs font-semibold text-[#1A1A1A] transition-colors"
            >
              Clear filters
            </button>
          </div>
        )}

        {/* Kanban Board */}
        {!isLoading && applications.length > 0 && !hasNoFilterResults && (
          <KanbanBoard
            applications={filteredApplications}
            onMoveApplication={handleMoveApplication}
            onSaveApplication={handleSaveApplication}
            onDeleteApplication={handleDeleteApplication}
          />
        )}

        {/* Add Application Modal from Header CTA */}
        <ApplicationModal
          isOpen={isAddModalOpen}
          onClose={() => setIsAddModalOpen(false)}
          onSave={handleSaveApplication}
          defaultStatus="applied"
        />
      </div>
    </DashboardLayout>
  );
}

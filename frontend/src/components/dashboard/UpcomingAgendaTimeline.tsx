import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { CalendarCheck, Clock, Calendar } from 'lucide-react';
import { UpcomingReminderItem } from '@/types/dashboard';
import { JobApplication } from '@/types/application';

interface UpcomingAgendaTimelineProps {
  reminders?: UpcomingReminderItem[];
  applications?: JobApplication[];
}

interface AgendaEvent {
  id: string;
  company: string;
  role: string;
  eventType: string;
  date: Date;
  dateFormatted: string;
  groupLabel: string;
  urgencyLabel: string;
  urgencyType: 'urgent' | 'warning' | 'normal';
  category: 'interview' | 'deadline';
}

export const UpcomingAgendaTimeline: React.FC<UpcomingAgendaTimelineProps> = ({
  reminders = [],
  applications = [],
}) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'all' | 'interview' | 'deadline'>('all');

  // Parse and aggregate agenda events from real reminders & application deadlines
  const events: AgendaEvent[] = useMemo(() => {
    const list: AgendaEvent[] = [];
    const now = new Date();

    // 1. Process explicit reminders from backend
    reminders.forEach((r) => {
      const d = r.dueDate ? new Date(r.dueDate) : new Date(now.getTime() + 24 * 3600 * 1000);
      const app = applications.find(
        (a) => a.company.toLowerCase() === (r.company || '').toLowerCase()
      );
      const company = r.company || app?.company || 'Organization';
      const role = app?.role || 'Position';
      const isInterview = r.type === 'interview';

      // Urgency calculation
      const diffHours = (d.getTime() - now.getTime()) / (1000 * 60 * 60);
      const diffDays = Math.ceil(diffHours / 24);

      let urgencyLabel = 'SCHEDULED';
      let urgencyType: 'urgent' | 'warning' | 'normal' = 'normal';

      if (diffHours <= 24 && diffHours > -12) {
        urgencyLabel = 'URGENT';
        urgencyType = 'urgent';
      } else if (diffDays >= 1 && diffDays <= 4) {
        urgencyLabel = `${diffDays} DAYS LEFT`;
        urgencyType = 'warning';
      }

      // Group header
      let groupLabel = '';
      const dayName = new Intl.DateTimeFormat('en-US', { weekday: 'long' }).format(d).toUpperCase();
      const monthDay = new Intl.DateTimeFormat('en-US', { month: 'short', day: '2-digit' }).format(d).toUpperCase();

      if (diffDays <= 1) {
        groupLabel = `TOMORROW · ${monthDay}`;
      } else if (diffDays <= 6) {
        groupLabel = `IN ${diffDays} DAYS · ${dayName}, ${monthDay}`;
      } else {
        groupLabel = `NEXT WEEK · ${dayName}, ${monthDay}`;
      }

      list.push({
        id: r.id,
        company,
        role,
        eventType: r.title,
        date: d,
        dateFormatted: r.dueText,
        groupLabel,
        urgencyLabel,
        urgencyType,
        category: isInterview ? 'interview' : 'deadline',
      });
    });

    // 2. Also incorporate applications with deadlines that might not be in reminders
    applications.forEach((a) => {
      if (!a.deadline) return;
      const d = new Date(a.deadline);
      if (isNaN(d.getTime())) return;
      // Skip if already in list
      if (list.some((ev) => ev.company.toLowerCase() === a.company.toLowerCase())) return;

      const diffHours = (d.getTime() - now.getTime()) / (1000 * 60 * 60);
      // Only show upcoming or recently due
      if (diffHours < -12) return;
      const diffDays = Math.ceil(diffHours / 24);

      let urgencyLabel = 'SCHEDULED';
      let urgencyType: 'urgent' | 'warning' | 'normal' = 'normal';

      if (diffHours <= 24 && diffHours > -12) {
        urgencyLabel = 'URGENT';
        urgencyType = 'urgent';
      } else if (diffDays >= 1 && diffDays <= 4) {
        urgencyLabel = `${diffDays} DAYS LEFT`;
        urgencyType = 'warning';
      }

      const dayName = new Intl.DateTimeFormat('en-US', { weekday: 'long' }).format(d).toUpperCase();
      const monthDay = new Intl.DateTimeFormat('en-US', { month: 'short', day: '2-digit' }).format(d).toUpperCase();

      let groupLabel = '';
      if (diffDays <= 1) {
        groupLabel = `TOMORROW · ${monthDay}`;
      } else if (diffDays <= 6) {
        groupLabel = `IN ${diffDays} DAYS · ${dayName}, ${monthDay}`;
      } else {
        groupLabel = `NEXT WEEK · ${dayName}, ${monthDay}`;
      }

      const isInterview = a.status === 'interview';
      const eventType = isInterview
        ? 'Scheduled Interview Round'
        : a.status === 'oa'
        ? 'Online Assessment Deadline'
        : 'Application Deadline';

      list.push({
        id: a.id,
        company: a.company,
        role: a.role,
        eventType,
        date: d,
        dateFormatted: new Intl.DateTimeFormat('en-US', {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
        }).format(d),
        groupLabel,
        urgencyLabel,
        urgencyType,
        category: isInterview ? 'interview' : 'deadline',
      });
    });

    // Sort chronologically
    return list.sort((a, b) => a.date.getTime() - b.date.getTime());
  }, [reminders, applications]);

  // Tab counts
  const interviewCount = events.filter((e) => e.category === 'interview').length;
  const deadlineCount = events.filter((e) => e.category === 'deadline').length;

  const filteredEvents = useMemo(() => {
    if (activeTab === 'interview') {
      return events.filter((e) => e.category === 'interview');
    }
    if (activeTab === 'deadline') {
      return events.filter((e) => e.category === 'deadline');
    }
    return events;
  }, [events, activeTab]);

  // Group events by groupLabel
  const grouped = useMemo(() => {
    const map = new Map<string, AgendaEvent[]>();
    filteredEvents.forEach((ev) => {
      const existing = map.get(ev.groupLabel) || [];
      existing.push(ev);
      map.set(ev.groupLabel, existing);
    });
    return Array.from(map.entries());
  }, [filteredEvents]);

  return (
    <div className="rounded-lg border border-[#E2E2E2] bg-white p-5 sm:p-6 shadow-2xs flex flex-col justify-between">
      {/* Header and Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#F0F0F0]">
        <h3 className="font-serif text-[18px] font-bold text-[#1A1A1A] tracking-tight flex items-center gap-2">
          <CalendarCheck size={17} className="text-[#1B2A4A]" />
          <span>Upcoming Agenda</span>
        </h3>

        {/* Tab Controls */}
        <div className="inline-flex items-center rounded-md border border-[#E2E2E2] bg-[#F5F5F7] p-0.5 self-start sm:self-center">
          <button
            type="button"
            onClick={() => setActiveTab('all')}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition-all cursor-pointer ${
              activeTab === 'all'
                ? 'bg-white text-[#1A1A1A] shadow-2xs font-semibold'
                : 'text-[#6B6B6B] hover:text-[#1A1A1A]'
            }`}
          >
            All ({events.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('interview')}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition-all cursor-pointer ${
              activeTab === 'interview'
                ? 'bg-white text-[#1A1A1A] shadow-2xs font-semibold'
                : 'text-[#6B6B6B] hover:text-[#1A1A1A]'
            }`}
          >
            Interviews ({interviewCount})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('deadline')}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition-all cursor-pointer ${
              activeTab === 'deadline'
                ? 'bg-white text-[#1A1A1A] shadow-2xs font-semibold'
                : 'text-[#6B6B6B] hover:text-[#1A1A1A]'
            }`}
          >
            Deadlines ({deadlineCount})
          </button>
        </div>
      </div>

      {/* Vertical Timeline Content */}
      <div className="py-4">
        {filteredEvents.length === 0 ? (
          <div className="py-10 text-center flex flex-col items-center justify-center">
            <p className="text-[13px] font-medium text-[#1A1A1A]">
              No upcoming agenda events
            </p>
            <p className="text-[11.5px] text-[#6B6B6B] mt-0.5 max-w-sm">
              Add upcoming application deadlines and interview rounds in Track Jobs to organize your schedule here.
            </p>
          </div>
        ) : (
          <div className="relative pl-4 space-y-6 before:absolute before:left-[7px] before:top-2 before:bottom-2 before:w-[1.5px] before:bg-[#E5E7EB]">
            {grouped.map(([groupLabel, items]) => (
              <div key={groupLabel} className="space-y-3 relative">
                {/* Node dot and group header */}
                <div className="flex items-center gap-2.5 -ml-[13px]">
                  <span className="w-3 h-3 rounded-full bg-[#1B2A4A] border-2 border-white ring-2 ring-[#E5E7EB] shrink-0" />
                  <span className="font-mono text-[10.5px] font-semibold uppercase tracking-wider text-[#6B6B6B]">
                    {groupLabel}
                  </span>
                </div>

                {/* Items in this date group */}
                <div className="space-y-2.5 pl-3">
                  {items.map((item) => {
                    const firstLetter = item.company.trim().charAt(0).toUpperCase();

                    return (
                      <div
                        key={item.id}
                        onClick={() => navigate('/track-jobs')}
                        className="rounded-lg border border-[#EAEAEA] bg-white hover:bg-[#FAFBFD] p-3.5 transition-all duration-180 cursor-pointer flex items-start justify-between gap-3 group"
                      >
                        <div className="flex items-start gap-3 min-w-0">
                          {/* Company monogram */}
                          <div className="w-8 h-8 rounded border border-[#E2E2E2] bg-[#F8F9FA] text-[#1B2A4A] font-bold text-xs flex items-center justify-center shrink-0 uppercase">
                            {firstLetter}
                          </div>

                          <div className="min-w-0">
                            <h4 className="text-[13.5px] font-bold text-[#1A1A1A] group-hover:text-[#1B2A4A] transition-colors truncate">
                              <span>{item.company}</span>
                              <span className="font-normal text-[#6B6B6B] mx-1.5">·</span>
                              <span className="font-medium text-[#4B5563]">{item.role}</span>
                            </h4>
                            <p className="text-[12px] text-[#6B6B6B] mt-0.5">
                              {item.eventType}
                            </p>
                            <div className="flex items-center gap-1 text-[11px] text-[#8E8E93] mt-1 font-mono">
                              {item.category === 'interview' ? (
                                <Clock size={11} className="text-[#8E8E93]" />
                              ) : (
                                <Calendar size={11} className="text-[#8E8E93]" />
                              )}
                              <span>{item.dateFormatted}</span>
                            </div>
                          </div>
                        </div>

                        {/* Urgency Badge */}
                        <div className="shrink-0">
                          {item.urgencyType === 'urgent' && (
                            <span className="px-2 py-0.5 rounded font-mono text-[9.5px] font-semibold bg-[#FEF2F2] border border-[#FECACA] text-[#B91C1C] tracking-wide">
                              {item.urgencyLabel}
                            </span>
                          )}
                          {item.urgencyType === 'warning' && (
                            <span className="px-2 py-0.5 rounded font-mono text-[9.5px] font-semibold bg-[#EFF6FF] border border-[#BFDBFE] text-[#1D4ED8] tracking-wide">
                              {item.urgencyLabel}
                            </span>
                          )}
                          {item.urgencyType === 'normal' && (
                            <span className="px-2 py-0.5 rounded font-mono text-[9.5px] font-semibold bg-[#F3F4F6] border border-[#E5E7EB] text-[#4B5563] tracking-wide">
                              {item.urgencyLabel}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer Link */}
      <div className="pt-3 border-t border-[#F0F0F0] text-center">
        <button
          type="button"
          onClick={() => navigate('/track-jobs')}
          className="text-[12px] font-medium text-[#1B2A4A] hover:text-[#253961] hover:underline transition-all cursor-pointer inline-flex items-center gap-1"
        >
          <span>Synchronize full calendar ledger</span>
          <span>→</span>
        </button>
      </div>
    </div>
  );
};

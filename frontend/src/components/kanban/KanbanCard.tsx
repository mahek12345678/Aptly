import { Draggable } from '@hello-pangea/dnd';
import { MapPin, Calendar, DollarSign, ExternalLink } from 'lucide-react';
import { JobApplication, KANBAN_STAGES } from '@/types/application';
import { formatDeadlineInfo } from '@/lib/deadline-utils';

interface KanbanCardProps {
  application: JobApplication;
  index: number;
  onClick: (application: JobApplication) => void;
}

export function KanbanCard({
  application,
  index,
  onClick,
}: KanbanCardProps) {
  const deadlineInfo = formatDeadlineInfo(application.deadline);
  const stage = KANBAN_STAGES.find((s) => s.id === application.status);

  return (
    <Draggable draggableId={application.id} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          onClick={() => onClick(application)}
          className={`group relative p-3.5 rounded-lg border bg-white transition-all cursor-grab active:cursor-grabbing text-left select-none ${
            snapshot.isDragging
              ? 'border-[#1B2A4A] shadow-md scale-[1.02] ring-1 ring-[#1B2A4A]/10 z-50'
              : 'border-[#E2E2E2] hover:border-[#CBD5E1] hover:shadow-xs'
          }`}
          style={provided.draggableProps.style}
        >
          {/* Header: Company & Status Pill */}
          <div className="flex items-start justify-between gap-2 mb-1">
            <h4 className="text-sm font-semibold text-[#1A1A1A] truncate tracking-tight">
              {application.company}
            </h4>

            {stage && (
              <span
                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium shrink-0"
                style={{
                  backgroundColor: stage.badgeBg,
                  color: stage.badgeText,
                }}
              >
                <span
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ backgroundColor: stage.dotColor }}
                />
                {stage.label}
              </span>
            )}
          </div>

          {/* Role */}
          <p className="text-xs text-[#4B5563] truncate font-normal mb-2.5">
            {application.role}
          </p>

          {/* Metadata chips */}
          <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-[#6B6B6B]">
            {application.location && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#F8FAFC] border border-[#E2E8F0] text-[#64748B] max-w-[140px] truncate">
                <MapPin size={10} className="shrink-0 text-[#94A3B8]" />
                <span className="truncate">{application.location}</span>
              </span>
            )}

            {application.stipend && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[#F8FAFC] border border-[#E2E8F0] text-[#64748B]">
                <DollarSign size={10} className="shrink-0 text-[#94A3B8]" />
                <span>{application.stipend}</span>
              </span>
            )}

            {deadlineInfo && (
              <span
                className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium border ${
                  deadlineInfo.isOverdue
                    ? 'bg-[#FEF2F2] border-[#FCA5A5] text-[#991B1B]'
                    : deadlineInfo.isUrgent
                    ? 'bg-[#FFFBEB] border-[#FDE68A] text-[#B45309]'
                    : 'bg-[#F8FAFC] border-[#E2E8F0] text-[#64748B]'
                }`}
              >
                <Calendar size={10} className="shrink-0" />
                <span>{deadlineInfo.text}</span>
              </span>
            )}

            {application.application_url && (
              <a
                href={application.application_url}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="inline-flex items-center p-1 rounded hover:bg-[#F1F5F9] text-[#94A3B8] hover:text-[#1B2A4A] ml-auto transition-colors"
                title="Open job posting"
              >
                <ExternalLink size={11} />
              </a>
            )}
          </div>
        </div>
      )}
    </Draggable>
  );
};

import { Droppable } from '@hello-pangea/dnd';
import { Plus } from 'lucide-react';
import { JobApplication, KanbanStage } from '@/types/application';
import { KanbanCard } from './KanbanCard';

interface KanbanColumnProps {
  stage: KanbanStage;
  applications: JobApplication[];
  onCardClick: (application: JobApplication) => void;
  onAddClick: (stageId: string) => void;
}

export function KanbanColumn({
  stage,
  applications,
  onCardClick,
  onAddClick,
}: KanbanColumnProps) {
  return (
    <div className="flex flex-col flex-1 min-w-[260px] max-w-[320px] bg-[#FAFAFA] rounded-xl border border-[#E5E7EB] p-2.5 h-[calc(100vh-210px)] min-h-[500px]">
      {/* Column Header */}
      <div
        className="flex items-center justify-between px-2.5 py-1.5 mb-2 rounded-lg border transition-colors"
        style={{
          backgroundColor: stage.headerBg || '#F9FAFB',
          borderColor: stage.headerBorder || '#E5E7EB',
        }}
      >
        <div className="flex items-center gap-2">
          <span
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: stage.dotColor }}
          />
          <h3 className="text-xs font-bold text-[#1B2A4A] tracking-tight uppercase">
            {stage.label}
          </h3>
          <span
            className="px-1.5 py-0.2 rounded-full text-[11px] font-semibold"
            style={{
              backgroundColor: stage.countBg || '#E5E7EB',
              color: stage.countText || '#4B5563',
            }}
          >
            {applications.length}
          </span>
        </div>

        <button
          type="button"
          onClick={() => onAddClick(stage.id)}
          className="p-1 rounded-md text-[#9CA3AF] hover:text-[#1B2A4A] hover:bg-white/80 border border-transparent hover:border-[#E5E7EB] transition-colors"
          title={`Add application to ${stage.label}`}
        >
          <Plus size={14} />
        </button>
      </div>

      {/* Droppable Area */}
      <Droppable droppableId={stage.id}>
        {(provided, snapshot) => (
          <div
            ref={provided.innerRef}
            {...provided.droppableProps}
            className={`flex-1 overflow-y-auto space-y-2 pr-0.5 rounded-lg transition-colors p-1 ${
              snapshot.isDraggingOver ? 'bg-[#F1F5F9]/80 ring-1 ring-[#3D5580]/20' : ''
            }`}
          >
            {applications.map((app, index) => (
              <KanbanCard
                key={app.id}
                application={app}
                index={index}
                onClick={onCardClick}
              />
            ))}
            {provided.placeholder}

            {applications.length === 0 && !snapshot.isDraggingOver && (
              <div className="h-28 border border-dashed border-[#D1D5DB] rounded-lg flex flex-col items-center justify-center p-3 text-center">
                <p className="text-[11px] text-[#9CA3AF]">No applications in {stage.label}</p>
                <button
                  type="button"
                  onClick={() => onAddClick(stage.id)}
                  className="mt-1 text-[11px] text-[#3D5580] hover:underline font-medium"
                >
                  + Add one
                </button>
              </div>
            )}
          </div>
        )}
      </Droppable>
    </div>
  );
};

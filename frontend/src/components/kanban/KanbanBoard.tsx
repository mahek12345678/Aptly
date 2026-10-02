import { useState, useEffect } from 'react';
import { DragDropContext, DropResult } from '@hello-pangea/dnd';
import {
  ApplicationStatus,
  CreateApplicationPayload,
  JobApplication,
  KANBAN_STAGES,
  UpdateApplicationPayload,
} from '@/types/application';
import { KanbanColumn } from './KanbanColumn';
import { ApplicationModal } from './ApplicationModal';

interface KanbanBoardProps {
  applications: JobApplication[];
  onMoveApplication: (id: string, newStatus: ApplicationStatus) => Promise<void>;
  onSaveApplication: (payload: CreateApplicationPayload | UpdateApplicationPayload, id?: string) => Promise<void>;
  onDeleteApplication: (id: string) => Promise<void>;
}

export function KanbanBoard({
  applications,
  onMoveApplication,
  onSaveApplication,
  onDeleteApplication,
}: KanbanBoardProps) {
  // Local optimistic state
  const [boardApps, setBoardApps] = useState<JobApplication[]>(applications);
  const [activeModalApp, setActiveModalApp] = useState<JobApplication | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [defaultStageForAdd, setDefaultStageForAdd] = useState<ApplicationStatus>('applied');
  const [moveError, setMoveError] = useState<string | null>(null);

  // Sync with prop when external applications change
  useEffect(() => {
    setBoardApps(applications);
  }, [applications]);

  const handleDragEnd = async (result: DropResult) => {
    const { destination, source, draggableId } = result;

    if (!destination) return;
    if (
      destination.droppableId === source.droppableId &&
      destination.index === source.index
    ) {
      return;
    }

    const sourceStatus = source.droppableId as ApplicationStatus;
    const destStatus = destination.droppableId as ApplicationStatus;

    // Snapshot previous state for rollback
    const previousApps = [...boardApps];

    // Optimistically update status
    setBoardApps((prev) =>
      prev.map((app) =>
        app.id === draggableId ? { ...app, status: destStatus } : app
      )
    );

    // If stage actually changed, call backend PATCH
    if (sourceStatus !== destStatus) {
      try {
        setMoveError(null);
        await onMoveApplication(draggableId, destStatus);
      } catch (err: any) {
        // Rollback on failure
        setBoardApps(previousApps);
        setMoveError(
          err?.response?.data?.detail || 'Failed to update application status. Reverted.'
        );
        setTimeout(() => setMoveError(null), 4000);
      }
    }
  };

  const handleCardClick = (app: JobApplication) => {
    setActiveModalApp(app);
    setIsModalOpen(true);
  };

  const handleAddClick = (stageId: string) => {
    setActiveModalApp(null);
    setDefaultStageForAdd(stageId as ApplicationStatus);
    setIsModalOpen(true);
  };

  return (
    <div className="relative">
      {/* Rollback Error Notice */}
      {moveError && (
        <div className="mb-4 p-3 rounded-lg bg-[#FEF2F2] border border-[#FCA5A5] text-[#991B1B] text-xs flex items-center justify-between shadow-xs">
          <span>{moveError}</span>
          <button
            type="button"
            onClick={() => setMoveError(null)}
            className="text-[#991B1B] hover:text-[#7F1D1D] font-bold text-sm ml-2"
          >
            ×
          </button>
        </div>
      )}

      {/* Drag & Drop Context */}
      <DragDropContext onDragEnd={handleDragEnd}>
        <div className="flex gap-3 overflow-x-auto pb-6 pt-1 items-start snap-x">
          {KANBAN_STAGES.map((stage) => {
            const columnApps = boardApps.filter((app) => app.status === stage.id);
            return (
              <div key={stage.id} className="snap-start shrink-0">
                <KanbanColumn
                  stage={stage}
                  applications={columnApps}
                  onCardClick={handleCardClick}
                  onAddClick={handleAddClick}
                />
              </div>
            );
          })}
        </div>
      </DragDropContext>

      {/* Add / Edit Modal */}
      <ApplicationModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={onSaveApplication}
        onDelete={onDeleteApplication}
        initialApplication={activeModalApp}
        defaultStatus={defaultStageForAdd}
      />
    </div>
  );
};

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar, FileCheck, ChevronRight, ArrowRight } from 'lucide-react';
import { UpcomingReminderItem } from '@/types/dashboard';

interface UpcomingRemindersProps {
  reminders?: UpcomingReminderItem[];
}

const defaultReminders: UpcomingReminderItem[] = [
  {
    id: '1',
    title: 'Complete Microsoft application',
    dueText: 'Due tomorrow',
    type: 'application',
  },
  {
    id: '2',
    title: 'Prepare for Amazon OA',
    dueText: 'In 3 days',
    type: 'assessment',
  },
  {
    id: '3',
    title: 'Follow up on Google application',
    dueText: 'In 5 days',
    type: 'followup',
  },
];

export const UpcomingReminders: React.FC<UpcomingRemindersProps> = ({
  reminders = defaultReminders,
}) => {
  const navigate = useNavigate();

  const getIcon = (type: UpcomingReminderItem['type']) => {
    switch (type) {
      case 'followup':
        return <FileCheck size={17} className="text-[#2563EB]" />;
      default:
        return <Calendar size={17} className="text-[#2563EB]" />;
    }
  };

  return (
    <div className="rounded-2xl bg-white border border-[#E2E2E2] p-5.5 sm:p-6 shadow-2xs">
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 border-b border-[#F0F0F0]">
        <h3 className="font-serif text-[18px] font-bold text-[#1A1A1A] tracking-tight">
          Upcoming Reminders
        </h3>
        <button
          type="button"
          onClick={() => navigate('/track-jobs')}
          className="group inline-flex items-center gap-1 text-[12.5px] font-semibold text-[#2563EB] hover:text-[#1D4ED8] transition-colors"
        >
          <span>View all</span>
          <ArrowRight
            size={13}
            className="group-hover:translate-x-0.5 transition-transform"
          />
        </button>
      </div>

      {/* Items or Empty State */}
      {reminders.length === 0 ? (
        <div className="py-7 text-center">
          <p className="text-[13px] font-medium text-[#475569]">
            No deadlines this week
          </p>
          <p className="text-[11.5px] text-[#94A3B8] mt-0.5">
            Upcoming application deadlines &amp; tasks will show here.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-[#F5F5F5] mt-1">
          {reminders.map((item) => (
            <div
              key={item.id}
              onClick={() => navigate('/track-jobs')}
              className="group py-3 flex items-center justify-between gap-3 cursor-pointer hover:bg-[#FAFBFD] -mx-2 px-2 rounded-xl transition-all duration-180"
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-8.5 h-8.5 rounded-xl bg-[#EFF6FF] border border-[#DBEAFE] flex items-center justify-center shrink-0">
                  {getIcon(item.type)}
                </div>
                <div className="min-w-0">
                  <h4 className="text-[13px] font-bold text-[#1A1A1A] group-hover:text-[#1B2A4A] transition-colors truncate">
                    {item.title}
                  </h4>
                  <p className="text-[11.5px] text-[#6B7280]">
                    {item.dueText}
                  </p>
                </div>
              </div>

              <ChevronRight
                size={15}
                className="text-[#9CA3AF] group-hover:text-[#1A1A1A] group-hover:translate-x-0.5 transition-all shrink-0"
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

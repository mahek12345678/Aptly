export interface DeadlineInfo {
  text: string;
  isOverdue: boolean;
  isUrgent: boolean; // Under 7 days or overdue
  daysDiff: number;
}

export function formatDeadlineInfo(deadlineStr?: string | null): DeadlineInfo | null {
  if (!deadlineStr) return null;

  const deadline = new Date(deadlineStr);
  if (isNaN(deadline.getTime())) return null;

  const now = new Date();
  // Normalize both dates to midnight local for clean day diff
  const todayMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const dlMidnight = new Date(deadline.getFullYear(), deadline.getMonth(), deadline.getDate());

  const msPerDay = 1000 * 60 * 60 * 24;
  const daysDiff = Math.round((dlMidnight.getTime() - todayMidnight.getTime()) / msPerDay);

  if (daysDiff < 0) {
    return {
      text: 'Overdue',
      isOverdue: true,
      isUrgent: true,
      daysDiff,
    };
  }

  if (daysDiff === 0) {
    return {
      text: 'Due today',
      isOverdue: false,
      isUrgent: true,
      daysDiff,
    };
  }

  if (daysDiff === 1) {
    return {
      text: '1 day left',
      isOverdue: false,
      isUrgent: true,
      daysDiff,
    };
  }

  if (daysDiff <= 7) {
    return {
      text: `${daysDiff} days left`,
      isOverdue: false,
      isUrgent: true,
      daysDiff,
    };
  }

  // Over 7 days: clean format like "14 Oct"
  const formatted = deadline.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });

  return {
    text: formatted,
    isOverdue: false,
    isUrgent: false,
    daysDiff,
  };
}

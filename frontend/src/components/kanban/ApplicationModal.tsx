import { useState, useEffect, FormEvent } from 'react';
import { X, Trash2, AlertTriangle, ExternalLink, Calendar, MapPin, DollarSign } from 'lucide-react';
import {
  ApplicationStatus,
  CreateApplicationPayload,
  JobApplication,
  KANBAN_STAGES,
  UpdateApplicationPayload,
} from '@/types/application';

interface ApplicationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (payload: CreateApplicationPayload | UpdateApplicationPayload, id?: string) => Promise<void>;
  onDelete?: (id: string) => Promise<void>;
  initialApplication?: JobApplication | null;
  defaultStatus?: ApplicationStatus;
}

export function ApplicationModal({
  isOpen,
  onClose,
  onSave,
  onDelete,
  initialApplication,
  defaultStatus = 'applied',
}: ApplicationModalProps) {
  const isEditing = Boolean(initialApplication);

  const [company, setCompany] = useState('');
  const [role, setRole] = useState('');
  const [status, setStatus] = useState<ApplicationStatus>(defaultStatus);
  const [location, setLocation] = useState('');
  const [deadline, setDeadline] = useState('');
  const [stipend, setStipend] = useState('');
  const [applicationUrl, setApplicationUrl] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [notes, setNotes] = useState('');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (initialApplication) {
      setCompany(initialApplication.company || '');
      setRole(initialApplication.role || '');
      setStatus(initialApplication.status || 'applied');
      setLocation(initialApplication.location || '');
      // Format deadline to YYYY-MM-DD for date input
      if (initialApplication.deadline) {
        const d = new Date(initialApplication.deadline);
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        setDeadline(`${yyyy}-${mm}-${dd}`);
      } else {
        setDeadline('');
      }
      setStipend(initialApplication.stipend || '');
      setApplicationUrl(initialApplication.application_url || '');
      setJobDescription(initialApplication.job_description || '');
      setNotes(initialApplication.notes || '');
    } else {
      setCompany('');
      setRole('');
      setStatus(defaultStatus);
      setLocation('');
      setDeadline('');
      setStipend('');
      setApplicationUrl('');
      setJobDescription('');
      setNotes('');
    }
    setShowDeleteConfirm(false);
    setErrorMessage(null);
  }, [initialApplication, defaultStatus, isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!company.trim() || !role.trim()) {
      setErrorMessage('Company and Role are required.');
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const payload: CreateApplicationPayload | UpdateApplicationPayload = {
        company: company.trim(),
        role: role.trim(),
        status,
        location: location.trim() || null,
        deadline: deadline ? new Date(deadline).toISOString() : null,
        stipend: stipend.trim() || null,
        application_url: applicationUrl.trim() || null,
        job_description: jobDescription.trim() || null,
        notes: notes.trim() || null,
      };

      await onSave(payload, initialApplication?.id);
      onClose();
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || err?.message || 'Failed to save application.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!initialApplication || !onDelete) return;
    setIsDeleting(true);
    try {
      await onDelete(initialApplication.id);
      onClose();
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.detail || err?.message || 'Failed to delete application.');
      setIsDeleting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-2xs transition-opacity animate-in fade-in duration-200">
      <div
        className="w-full max-w-xl bg-white rounded-xl border border-[#E2E2E2] shadow-lg flex flex-col max-h-[92vh] overflow-hidden transition-all scale-in-95 duration-200"
        role="dialog"
        aria-modal="true"
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E2E2E2] bg-[#FAFAFA]">
          <div>
            <h2 className="text-base font-bold text-[#1A1A1A] tracking-tight">
              {isEditing ? 'Edit Application' : 'Add Application'}
            </h2>
            <p className="text-xs text-[#6B6B6B] mt-0.5">
              {isEditing
                ? 'Update application status and details'
                : 'Track a new opportunity in your pipeline'}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-[#E5E7EB] transition-colors"
            title="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-4">
          {errorMessage && (
            <div className="p-3 rounded-lg bg-[#FEF2F2] border border-[#FCA5A5] text-[#991B1B] text-xs flex items-center gap-2">
              <AlertTriangle size={15} className="shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Row 1: Company & Role */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#1A1A1A] mb-1.5">
                Company <span className="text-[#991B1B]">*</span>
              </label>
              <input
                type="text"
                required
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="e.g. Stripe, Linear"
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E2E2E2] focus:border-[#1B2A4A] focus:outline-none focus:ring-1 focus:ring-[#1B2A4A] bg-[#FFFFFF] text-[#1A1A1A] placeholder:text-[#9CA3AF]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#1A1A1A] mb-1.5">
                Role / Title <span className="text-[#991B1B]">*</span>
              </label>
              <input
                type="text"
                required
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="e.g. Frontend Engineer"
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E2E2E2] focus:border-[#1B2A4A] focus:outline-none focus:ring-1 focus:ring-[#1B2A4A] bg-[#FFFFFF] text-[#1A1A1A] placeholder:text-[#9CA3AF]"
              />
            </div>
          </div>

          {/* Row 2: Status & Location */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#1A1A1A] mb-1.5">
                Status Stage
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as ApplicationStatus)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E2E2E2] focus:border-[#1B2A4A] focus:outline-none focus:ring-1 focus:ring-[#1B2A4A] bg-[#FFFFFF] text-[#1A1A1A]"
              >
                {KANBAN_STAGES.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#1A1A1A] mb-1.5 flex items-center gap-1">
                <MapPin size={12} className="text-[#6B6B6B]" />
                <span>Location</span>
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. San Francisco, Remote"
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E2E2E2] focus:border-[#1B2A4A] focus:outline-none focus:ring-1 focus:ring-[#1B2A4A] bg-[#FFFFFF] text-[#1A1A1A] placeholder:text-[#9CA3AF]"
              />
            </div>
          </div>

          {/* Row 3: Deadline & Compensation */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#1A1A1A] mb-1.5 flex items-center gap-1">
                <Calendar size={12} className="text-[#6B6B6B]" />
                <span>Deadline</span>
              </label>
              <input
                type="date"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E2E2E2] focus:border-[#1B2A4A] focus:outline-none focus:ring-1 focus:ring-[#1B2A4A] bg-[#FFFFFF] text-[#1A1A1A]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#1A1A1A] mb-1.5 flex items-center gap-1">
                <DollarSign size={12} className="text-[#6B6B6B]" />
                <span>Compensation / Stipend</span>
              </label>
              <input
                type="text"
                value={stipend}
                onChange={(e) => setStipend(e.target.value)}
                placeholder="e.g. $140,000 / yr"
                className="w-full px-3 py-2 text-xs rounded-lg border border-[#E2E2E2] focus:border-[#1B2A4A] focus:outline-none focus:ring-1 focus:ring-[#1B2A4A] bg-[#FFFFFF] text-[#1A1A1A] placeholder:text-[#9CA3AF]"
              />
            </div>
          </div>

          {/* Row 4: Job URL */}
          <div>
            <label className="block text-xs font-semibold text-[#1A1A1A] mb-1.5 flex items-center gap-1">
              <ExternalLink size={12} className="text-[#6B6B6B]" />
              <span>Job Posting URL</span>
            </label>
            <input
              type="url"
              value={applicationUrl}
              onChange={(e) => setApplicationUrl(e.target.value)}
              placeholder="https://company.com/careers/role"
              className="w-full px-3 py-2 text-xs rounded-lg border border-[#E2E2E2] focus:border-[#1B2A4A] focus:outline-none focus:ring-1 focus:ring-[#1B2A4A] bg-[#FFFFFF] text-[#1A1A1A] placeholder:text-[#9CA3AF]"
            />
          </div>

          {/* Row 5: Notes */}
          <div>
            <label className="block text-xs font-semibold text-[#1A1A1A] mb-1.5">
              Personal Notes
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Contacts, referral info, recruiter communication, etc."
              className="w-full px-3 py-2 text-xs rounded-lg border border-[#E2E2E2] focus:border-[#1B2A4A] focus:outline-none focus:ring-1 focus:ring-[#1B2A4A] bg-[#FFFFFF] text-[#1A1A1A] placeholder:text-[#9CA3AF] resize-none"
            />
          </div>

          {/* Row 6: Job Description */}
          <div>
            <label className="block text-xs font-semibold text-[#1A1A1A] mb-1.5">
              Job Description (Optional)
            </label>
            <textarea
              rows={3}
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste job description or requirements here..."
              className="w-full px-3 py-2 text-xs rounded-lg border border-[#E2E2E2] focus:border-[#1B2A4A] focus:outline-none focus:ring-1 focus:ring-[#1B2A4A] bg-[#FFFFFF] text-[#1A1A1A] placeholder:text-[#9CA3AF] resize-none"
            />
          </div>

          {/* Delete Confirmation Box */}
          {showDeleteConfirm && (
            <div className="p-3 rounded-lg bg-[#FEF2F2] border border-[#FCA5A5] flex items-center justify-between gap-3 animate-in fade-in duration-150">
              <div className="text-xs text-[#991B1B] font-medium">
                Are you sure you want to delete this application?
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(false)}
                  className="px-2.5 py-1 text-xs rounded bg-white border border-[#D1D5DB] text-[#374151] hover:bg-[#F3F4F6]"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="px-2.5 py-1 text-xs rounded bg-[#991B1B] text-white hover:bg-[#7F1D1D] font-medium disabled:opacity-50"
                >
                  {isDeleting ? 'Deleting...' : 'Confirm Delete'}
                </button>
              </div>
            </div>
          )}

          {/* Footer Actions */}
          <div className="pt-3 border-t border-[#E2E2E2] flex items-center justify-between gap-3">
            {isEditing && onDelete ? (
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(true)}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium text-[#991B1B] hover:bg-[#FEF2F2] transition-colors"
              >
                <Trash2 size={13} />
                <span>Delete</span>
              </button>
            ) : (
              <div />
            )}

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-medium text-[#374151] bg-[#FFFFFF] border border-[#D1D5DB] rounded-lg hover:bg-[#F3F4F6] transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-4 py-2 text-xs font-semibold text-white bg-[#1B2A4A] hover:bg-[#142038] rounded-lg transition-colors shadow-xs disabled:opacity-50"
              >
                {isSubmitting ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Application'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import { X, Check } from 'lucide-react';
import { api } from '@/lib/api';

export interface ProfilePreferences {
  user_type?: string | null;
  opportunity_type?: string | null;
  graduation_year?: number | null;
  preferred_location?: string | null;
  preferred_roles: string[];
  interests: string[];
}

export interface ProfilePersonalization {
  focus_opportunity_matching: boolean;
  focus_resume_tailoring: boolean;
  focus_deadline_tracking: boolean;
  update_frequency: string;
  additional_notes?: string | null;
}

interface EditProfileDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  preferences: ProfilePreferences | null;
  personalization: ProfilePersonalization | null;
  onSaved: () => void;
}

export const EditProfileDrawer: React.FC<EditProfileDrawerProps> = ({
  isOpen,
  onClose,
  preferences,
  personalization,
  onSaved,
}) => {
  const [preferredRoles, setPreferredRoles] = useState<string>('');
  const [opportunityType, setOpportunityType] = useState<string>('full_time');
  const [graduationYear, setGraduationYear] = useState<string>('');
  const [preferredLocation, setPreferredLocation] = useState<string>('');
  const [interests, setInterests] = useState<string>('');
  const [updateFrequency, setUpdateFrequency] = useState<string>('daily');
  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (preferences) {
      setPreferredRoles(preferences.preferred_roles?.join(', ') || '');
      setOpportunityType(preferences.opportunity_type || 'full_time');
      setGraduationYear(preferences.graduation_year ? String(preferences.graduation_year) : '');
      setPreferredLocation(preferences.preferred_location || '');
      setInterests(preferences.interests?.join(', ') || '');
    }
    if (personalization) {
      setUpdateFrequency(personalization.update_frequency || 'daily');
    }
  }, [preferences, personalization, isOpen]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setErrorMessage(null);

    const rolesArray = preferredRoles
      .split(',')
      .map((r) => r.trim())
      .filter(Boolean);

    const interestsArray = interests
      .split(',')
      .map((i) => i.trim())
      .filter(Boolean);

    const gradYearNum = graduationYear ? parseInt(graduationYear, 10) : null;

    try {
      // 1. Update preferences
      await api.put('/api/onboarding/preferences', {
        opportunity_type: opportunityType,
        graduation_year: gradYearNum,
        preferred_location: preferredLocation.trim(),
        preferred_roles: rolesArray,
        interests: interestsArray,
        user_type: preferences?.user_type || 'student',
      });

      // 2. Update personalization
      await api.put('/api/onboarding/personalization', {
        focus_opportunity_matching: personalization?.focus_opportunity_matching ?? true,
        focus_resume_tailoring: personalization?.focus_resume_tailoring ?? true,
        focus_deadline_tracking: personalization?.focus_deadline_tracking ?? true,
        update_frequency: updateFrequency,
        additional_notes: personalization?.additional_notes || null,
      });

      setSavedSuccess(true);
      setTimeout(() => {
        setSavedSuccess(false);
        onSaved();
        onClose();
      }, 700);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save changes. Please try again.';
      setErrorMessage(msg);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/30 backdrop-blur-xs transition-opacity duration-200"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-white border-l border-[#E2E2E2] shadow-xl flex flex-col justify-between animate-in slide-in-from-right duration-200">
          {/* Header */}
          <div className="p-5 border-b border-[#F0F0F0] flex items-center justify-between">
            <div>
              <span className="text-[10px] font-mono font-semibold tracking-wider text-[#6B6B6B] uppercase block">
                CAREER SETTINGS
              </span>
              <h2 className="font-serif text-xl font-bold text-[#1B2A4A]">Edit Profile</h2>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-[#F3F4F6] rounded-lg transition-colors cursor-pointer"
              aria-label="Close drawer"
            >
              <X size={18} />
            </button>
          </div>

          {/* Form Body */}
          <form id="edit-profile-form" onSubmit={handleSave} className="flex-1 overflow-y-auto p-5 space-y-4">
            {errorMessage && (
              <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs">
                {errorMessage}
              </div>
            )}

            {/* Target Roles */}
            <div>
              <label className="block text-xs font-semibold text-[#1B2A4A] mb-1">
                Target Roles
              </label>
              <input
                type="text"
                value={preferredRoles}
                onChange={(e) => setPreferredRoles(e.target.value)}
                placeholder="e.g. Software Engineer, Backend Engineer, SDE Intern"
                className="w-full px-3 py-2 text-xs border border-[#E2E2E2] rounded-lg focus:outline-none focus:border-[#1B2A4A] focus:ring-1 focus:ring-[#1B2A4A] bg-[#FAFAFA]"
              />
              <p className="text-[11px] text-[#6B6B6B] mt-1">Separate multiple roles with commas.</p>
            </div>

            {/* Opportunity Type */}
            <div>
              <label className="block text-xs font-semibold text-[#1B2A4A] mb-1">
                Opportunity Type
              </label>
              <select
                value={opportunityType}
                onChange={(e) => setOpportunityType(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-[#E2E2E2] rounded-lg focus:outline-none focus:border-[#1B2A4A] focus:ring-1 focus:ring-[#1B2A4A] bg-[#FAFAFA]"
              >
                <option value="full_time">Full-time</option>
                <option value="internship">Internship</option>
                <option value="both">Full-time &amp; Internship</option>
                <option value="contract">Contract / Co-op</option>
              </select>
            </div>

            {/* Work Mode */}
            <div>
              <label className="block text-xs font-semibold text-[#1B2A4A] mb-1">
                Preferred Work Mode
              </label>
              <select
                value={preferences?.user_type || 'hybrid'}
                onChange={(e) => {
                  if (preferences) preferences.user_type = e.target.value;
                }}
                className="w-full px-3 py-2 text-xs border border-[#E2E2E2] rounded-lg focus:outline-none focus:border-[#1B2A4A] focus:ring-1 focus:ring-[#1B2A4A] bg-[#FAFAFA]"
              >
                <option value="hybrid">Hybrid / Remote</option>
                <option value="remote">Remote Only</option>
                <option value="onsite">On-site</option>
              </select>
            </div>

            {/* Preferred Location */}
            <div>
              <label className="block text-xs font-semibold text-[#1B2A4A] mb-1">
                Preferred Location
              </label>
              <input
                type="text"
                value={preferredLocation}
                onChange={(e) => setPreferredLocation(e.target.value)}
                placeholder="e.g. Bengaluru, India or Remote"
                className="w-full px-3 py-2 text-xs border border-[#E2E2E2] rounded-lg focus:outline-none focus:border-[#1B2A4A] focus:ring-1 focus:ring-[#1B2A4A] bg-[#FAFAFA]"
              />
            </div>

            {/* Graduation Year */}
            <div>
              <label className="block text-xs font-semibold text-[#1B2A4A] mb-1">
                Graduation Year
              </label>
              <input
                type="number"
                value={graduationYear}
                onChange={(e) => setGraduationYear(e.target.value)}
                placeholder="e.g. 2026, 2027, 2028"
                className="w-full px-3 py-2 text-xs border border-[#E2E2E2] rounded-lg focus:outline-none focus:border-[#1B2A4A] focus:ring-1 focus:ring-[#1B2A4A] bg-[#FAFAFA]"
              />
            </div>

            {/* Interests / Domains */}
            <div>
              <label className="block text-xs font-semibold text-[#1B2A4A] mb-1">
                Interests &amp; Specializations
              </label>
              <input
                type="text"
                value={interests}
                onChange={(e) => setInterests(e.target.value)}
                placeholder="e.g. Distributed Systems, API Architecture, AI"
                className="w-full px-3 py-2 text-xs border border-[#E2E2E2] rounded-lg focus:outline-none focus:border-[#1B2A4A] focus:ring-1 focus:ring-[#1B2A4A] bg-[#FAFAFA]"
              />
              <p className="text-[11px] text-[#6B6B6B] mt-1">Comma-separated key technical interests.</p>
            </div>

            {/* Update Frequency */}
            <div className="pt-2 border-t border-[#F0F0F0]">
              <label className="block text-xs font-semibold text-[#1B2A4A] mb-1">
                Notification &amp; Digest Frequency
              </label>
              <select
                value={updateFrequency}
                onChange={(e) => setUpdateFrequency(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-[#E2E2E2] rounded-lg focus:outline-none focus:border-[#1B2A4A] focus:ring-1 focus:ring-[#1B2A4A] bg-[#FAFAFA]"
              >
                <option value="daily">Daily briefing (08:00 IST)</option>
                <option value="important_only">High-priority matches only</option>
                <option value="weekly">Weekly digest</option>
              </select>
            </div>
          </form>

          {/* Footer Actions */}
          <div className="p-4 border-t border-[#E2E2E2] bg-[#FAFAFA] flex items-center justify-between">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="px-4 py-2 rounded-lg border border-[#E2E2E2] bg-white text-xs font-medium text-[#1A1A1A] hover:bg-[#F3F4F6] transition-colors cursor-pointer"
            >
              Cancel
            </button>

            <button
              type="submit"
              form="edit-profile-form"
              disabled={isSaving}
              className="inline-flex items-center gap-1.5 px-5 py-2 rounded-lg bg-[#1B2A4A] hover:bg-[#142038] text-white text-xs font-semibold transition-colors cursor-pointer shadow-2xs disabled:opacity-60"
            >
              {savedSuccess ? (
                <>
                  <Check size={14} className="text-emerald-400" />
                  <span>Saved</span>
                </>
              ) : isSaving ? (
                <span>Saving...</span>
              ) : (
                <span>Save changes</span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

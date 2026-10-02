import React, { useState, useRef, useEffect, useMemo } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  Calendar,
  Bell,
  Menu,
  ChevronLeft,
} from 'lucide-react';
import { useAssistant } from '@/contexts/AssistantContext';
import { useAuth } from '@/contexts/AuthContext';

interface TopBarProps {
  onToggleSidebar?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({ onToggleSidebar }) => {
  const { openAssistant } = useAssistant();
  const { user } = useAuth();
  const location = useLocation();
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);

  // Formatted date matching screenshot (e.g., "Thursday, Oct 24")
  const formattedDate = useMemo(() => {
    const now = new Date();
    return new Intl.DateTimeFormat('en-US', {
      weekday: 'long',
      month: 'short',
      day: 'numeric',
    }).format(now);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        notifRef.current &&
        !notifRef.current.contains(event.target as Node)
      ) {
        setNotificationsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="h-14 px-4 sm:px-6 lg:px-8 border-b border-[#E2E2E2] bg-white flex items-center justify-between sticky top-0 z-30">
      {/* Left: Mobile Toggle + Date Indicator + Workspace / Ledger */}
      <div className="flex items-center gap-3 sm:gap-4">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="lg:hidden p-1.5 rounded-lg text-[#6B7280] hover:text-[#1A1A1A] hover:bg-[#F3F4F6] transition-colors"
          aria-label="Open navigation menu"
        >
          <Menu size={18} />
        </button>

        {/* Date Display */}
        <div className="flex items-center gap-2 text-[13px] font-medium text-[#4A5568]">
          <Calendar size={14} className="text-[#6B7280] shrink-0" />
          <span className="hidden sm:inline">{formattedDate}</span>
          <span className="sm:hidden">{formattedDate.split(',')[0]}</span>
        </div>

        {/* Vertical divider */}
        <div className="h-4 w-px bg-[#E2E2E2] hidden sm:block" />

        {/* Workspace / Ledger or Profile navigation */}
        <div className="hidden sm:flex items-center gap-3 text-[13.5px]">
          {location.pathname === '/profile' ? (
            <div className="flex items-center gap-1.5">
              <NavLink to="/dashboard" className="text-[#6B6B6B] hover:text-[#1A1A1A] transition-colors">
                Workspace
              </NavLink>
              <span className="text-[#9CA3AF]">/</span>
              <span className="font-semibold text-[#1A1A1A]">Profile</span>
            </div>
          ) : (
            <div className="flex items-center gap-4">
              <NavLink
                to="/dashboard"
                className={({ isActive }) =>
                  `font-semibold transition-colors ${
                    isActive ? 'text-[#1A1A1A]' : 'text-[#6B6B6B] hover:text-[#1A1A1A]'
                  }`
                }
              >
                Workspace
              </NavLink>
              <NavLink
                to="/track-jobs"
                className={({ isActive }) =>
                  `font-medium transition-colors ${
                    isActive ? 'text-[#1A1A1A] font-semibold' : 'text-[#6B6B6B] hover:text-[#1A1A1A]'
                  }`
                }
              >
                Ledger
              </NavLink>
            </div>
          )}
        </div>
      </div>

      {/* Right: Notifications, Ask Aptly button, and User Avatar */}
      <div className="flex items-center gap-2.5 sm:gap-3">
        {/* Notification Bell */}
        <div className="relative" ref={notifRef}>
          <button
            type="button"
            onClick={() => setNotificationsOpen(!notificationsOpen)}
            className="relative p-1.5 text-[#6B7280] hover:text-[#1A1A1A] rounded-lg hover:bg-[#F3F4F6] transition-colors cursor-pointer"
            aria-label="Notifications"
          >
            <Bell size={17} />
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-[#EA4335] ring-2 ring-white" />
          </button>

          {/* Notifications dropdown popover */}
          {notificationsOpen && (
            <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-lg border border-[#E2E2E2] p-3 z-50 animate-fade-in">
              <div className="flex items-center justify-between pb-2 border-b border-[#F0F0F0] px-1">
                <span className="text-[12.5px] font-bold text-[#1A1A1A]">Notifications</span>
                <span className="text-[11px] text-[#3D5580] font-medium cursor-pointer">Mark all read</span>
              </div>
              <div className="py-2 space-y-1.5 text-xs">
                <div className="p-2 rounded-lg bg-[#F8FAFC] hover:bg-[#F1F5F9] cursor-pointer transition-colors">
                  <p className="font-semibold text-[#1B2A4A]">Daily Briefing Ready</p>
                  <p className="text-[11px] text-[#6B7280]">Your personalized search update is ready.</p>
                </div>
                <div className="p-2 rounded-lg hover:bg-[#F8FAFC] cursor-pointer transition-colors">
                  <p className="font-semibold text-[#1B2A4A]">Matches Refreshed</p>
                  <p className="text-[11px] text-[#6B7280]">New positions available in Find Positions.</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Ask Aptly Dark Navy Button matching screenshot: < Ask Aptly */}
        <button
          type="button"
          onClick={() => openAssistant()}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#1B2A4A] hover:bg-[#142038] active:bg-[#0F182A] text-white text-[12.5px] font-semibold transition-colors cursor-pointer shadow-2xs"
          title="Open Ask Aptly (⌘K)"
        >
          <ChevronLeft size={14} className="stroke-[2.5]" />
          <span>Ask Aptly</span>
        </button>

        {/* User Circular Avatar matching screenshot */}
        <NavLink
          to="/profile"
          className="w-7 h-7 rounded-full bg-[#1B2A4A] text-white flex items-center justify-center text-[10.5px] font-bold overflow-hidden shrink-0 hover:ring-2 hover:ring-[#1B2A4A]/20 transition-all shadow-2xs select-none"
          title={user?.name || 'Profile & Account'}
        >
          {user?.profile_picture_url ? (
            <img
              src={user.profile_picture_url}
              alt={user?.name || 'User'}
              className="w-full h-full object-cover"
            />
          ) : (
            <span>
              {user?.name
                ? user.name
                    .split(' ')
                    .map((n: string) => n[0])
                    .slice(0, 2)
                    .join('')
                    .toUpperCase()
                : 'AM'}
            </span>
          )}
        </NavLink>
      </div>
    </header>
  );
};


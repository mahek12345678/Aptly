import React, { useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Briefcase,
  Search,
  FileText,
  Info,
  X,
  User,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { AptlyLogo } from '@/components/common/AptlyLogo';

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

const navItems = [
  {
    name: 'Dashboard',
    path: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    name: 'Track Jobs',
    path: '/track-jobs',
    icon: Briefcase,
  },
  {
    name: 'Find New Positions',
    path: '/find-positions',
    icon: Search,
  },
  {
    name: 'JD Analyzer',
    path: '/jd-analyzer',
    icon: FileText,
  },
  {
    name: 'About',
    path: '/about',
    icon: Info,
  },
];

export const Sidebar: React.FC<SidebarProps> = ({ isOpen = false, onClose }) => {
  const navigate = useNavigate();
  const { user } = useAuth();

  // Close mobile sidebar on Escape key
  useEffect(() => {
    if (!isOpen || !onClose) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  return (
    <>
      {/* Mobile overlay backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/25 z-40 lg:hidden backdrop-blur-xs transition-opacity"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-white border-r border-[#E2E2E2] flex flex-col justify-between transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0 shadow-xl' : '-translate-x-full'
        }`}
      >
        <div>
          {/* Brand Header */}
          <div className="px-5 pt-6 pb-5 flex items-center justify-between border-b border-[#F0F0F0] lg:border-b-0">
            <div
              className="flex items-center cursor-pointer select-none"
              onClick={() => {
                navigate('/dashboard');
                onClose?.();
              }}
            >
              <AptlyLogo height={34} variant="full" />
            </div>

            {/* Close button on mobile */}
            <button
              type="button"
              onClick={onClose}
              className="lg:hidden p-1.5 rounded-lg text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-[#F3F4F6] transition-colors"
              aria-label="Close sidebar"
            >
              <X size={18} />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="px-3 py-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => onClose?.()}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-lg text-[13.5px] font-medium transition-colors relative ${
                      isActive
                        ? 'bg-[#EEF4FC] text-[#1B2A4A] font-semibold'
                        : 'text-[#4A5568] hover:text-[#1A1A1A] hover:bg-[#F8FAFC]'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon
                        size={17}
                        className={isActive ? 'text-[#1B2A4A]' : 'text-[#718096]'}
                        strokeWidth={isActive ? 2.2 : 1.8}
                      />
                      <span>{item.name}</span>
                    </>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Bottom Profile & Account Footer matching screenshot */}
        <div className="border-t border-[#E2E2E2] p-3">
          <NavLink
            to="/profile"
            onClick={() => onClose?.()}
            className={({ isActive }) =>
              `w-full flex items-center justify-between px-3 py-2 rounded-lg text-[13px] font-medium transition-colors cursor-pointer ${
                isActive
                  ? 'bg-[#EEF4FC] text-[#1B2A4A] font-semibold'
                  : 'text-[#4A5568] hover:text-[#1A1A1A] hover:bg-[#F8FAFC]'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <div className="flex items-center gap-2.5 truncate">
                  {user?.profile_picture_url ? (
                    <img
                      src={user.profile_picture_url}
                      alt={user?.name || 'Profile'}
                      className="w-5 h-5 rounded-full object-cover shrink-0"
                    />
                  ) : (
                    <User
                      size={16}
                      className={isActive ? 'text-[#1B2A4A]' : 'text-[#6B6B6B] shrink-0'}
                    />
                  )}
                  <span className="truncate">Profile &amp; Account</span>
                </div>
                <kbd className="text-[10px] font-mono text-[#9CA3AF] tracking-widest uppercase">
                  ⌘P
                </kbd>
              </>
            )}
          </NavLink>
        </div>
      </aside>
    </>
  );
};

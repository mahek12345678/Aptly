import { useState, useRef, useEffect } from 'react';
import { HelpCircle, LogOut, ChevronDown, User as UserIcon } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { AptlyLogo } from '@/components/common/AptlyLogo';

export default function OnboardingHeader() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  // Get user initials (e.g. "MA")
  const getInitials = () => {
    if (!user?.name) return 'U';
    const parts = user.name.trim().split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return user.name.slice(0, 2).toUpperCase();
  };

  return (
    <header className="w-full bg-white border-b border-border/70 px-6 sm:px-10 py-4 flex items-center justify-between z-20">
      {/* Brand logo */}
      <AptlyLogo height={28} variant="full" />

      {/* Right controls */}
      <div className="flex items-center gap-3.5 sm:gap-5">
        {/* Companion Tagline */}
        <div className="hidden md:flex items-center gap-1.5 text-xs text-[#64748B]">
          <span className="text-[12.5px]">Your career companion, always here.</span>
        </div>

        {/* Vertical divider */}
        <div className="hidden md:block w-px h-4 bg-[#E2E8F0]" />

        {/* Need help button */}
        <a
          href="mailto:support@aptly.careers?subject=Aptly%20Onboarding%20Help"
          className="flex items-center gap-1.5 text-xs sm:text-[13px] font-medium text-[#475569] hover:text-[#0F172A] transition-subtle"
        >
          <HelpCircle size={16} strokeWidth={1.8} className="text-[#64748B]" />
          <span>Need help?</span>
        </a>

        {/* User profile avatar / menu */}
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setMenuOpen(!menuOpen)}
            className="flex items-center gap-1.5 p-1 rounded-full hover:bg-slate-100 transition-subtle focus:outline-none"
            aria-label="User profile menu"
            aria-expanded={menuOpen}
          >
            {user?.picture || user?.profile_picture_url ? (
              <img
                src={user.picture || user.profile_picture_url || ''}
                alt={user.name}
                className="w-8 h-8 rounded-full object-cover border border-border"
              />
            ) : (
              <div className="w-8 h-8 rounded-full bg-[#E2E8F0] text-[#1E293B] font-semibold text-xs flex items-center justify-center">
                {getInitials()}
              </div>
            )}
            <ChevronDown size={14} className="text-muted" />
          </button>

          {/* Dropdown Menu */}
          {menuOpen && (
            <div className="absolute right-0 mt-2 w-56 bg-surface border border-border rounded-xl shadow-lg py-2 z-50 animate-slide-up text-left">
              <div className="px-4 py-2 border-b border-border/50">
                <p className="text-xs font-semibold text-text truncate">{user?.name || 'User'}</p>
                <p className="text-xs text-muted truncate">{user?.email}</p>
              </div>

              <div className="py-1">
                <div className="px-4 py-1.5 text-xs text-muted flex items-center gap-2">
                  <UserIcon size={14} />
                  <span>Logged in via Google</span>
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full text-left px-4 py-2 text-xs text-red-600 hover:bg-red-50 flex items-center gap-2 transition-subtle"
                >
                  <LogOut size={14} />
                  <span>Sign out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { ApplicationIntentBanner } from '@/components/applications/ApplicationIntentBanner';
import { AptlyAssistantDrawer } from '@/components/assistant/AptlyAssistantDrawer';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#FAFAFA] text-[#1A1A1A] font-inter flex flex-col">
      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Content Area (offset by sidebar width on lg screens) */}
      <div className="lg:pl-64 flex flex-col min-h-screen">
        {/* TopBar */}
        <TopBar onToggleSidebar={() => setSidebarOpen(true)} />

        {/* Page Body */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-[1400px] w-full mx-auto">
          {children}
        </main>
      </div>

      {/* Automatic Application-Intent Confirmation Banner */}
      <ApplicationIntentBanner />

      {/* Single Global Ask Aptly Workspace Drawer */}
      <AptlyAssistantDrawer />
    </div>
  );
};

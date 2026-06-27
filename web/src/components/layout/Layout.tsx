import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { DegradedBanner } from "./DegradedBanner";
import { Sheet } from "../shared/Sheet";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { cn } from "@/lib/utils";

export default function Layout() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  // Register Vim-style navigation keyboard shortcuts globally
  useKeyboardShortcuts();

  const isFullWidth = location.pathname === "/logs";

  return (
    <div className="min-h-screen flex bg-background text-foreground">
      {/* Persistent Left Sidebar - Hidden on mobile, shown on md and above */}
      <Sidebar className="hidden md:flex w-64 flex-shrink-0" />

      {/* Mobile Drawer Navigation Sidebar */}
      <Sheet isOpen={isMobileMenuOpen} onClose={() => setIsMobileMenuOpen(false)}>
        <Sidebar className="border-r-0 p-0" onItemClick={() => setIsMobileMenuOpen(false)} />
      </Sheet>

      {/* Main Container Layout */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header TopBar */}
        <TopBar onMenuToggle={() => setIsMobileMenuOpen(true)} />

        {/* Global Degraded warning banner */}
        <DegradedBanner />

        {/* Main Content Pane */}
        <main className="flex-grow overflow-y-auto px-4 py-6 md:px-8">
          <div className={cn("mx-auto w-full", isFullWidth ? "max-w-none" : "max-w-6xl")}>
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

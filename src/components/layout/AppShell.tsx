"use client";

import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { CommandPalette } from "./CommandPalette";
import { GlobalDialogs } from "@/components/credentials/GlobalDialogs";
import { TooltipProvider } from "@/components/ui/tooltip";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <TooltipProvider>
      <div className="flex h-full min-h-0">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar />
          <main className="min-h-0 flex-1 overflow-auto p-4 md:p-5">{children}</main>
        </div>
      </div>
      <CommandPalette />
      <GlobalDialogs />
    </TooltipProvider>
  );
}

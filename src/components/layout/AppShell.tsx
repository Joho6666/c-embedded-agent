"use client";

import { useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { CommandPalette } from "./CommandPalette";
import { GlobalDialogs } from "@/components/credentials/GlobalDialogs";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useGateway } from "@/lib/stores/gateway";

export function AppShell({ children }: { children: React.ReactNode }) {
  const hydrate = useGateway((s) => s.hydrate);
  const hydrated = useGateway((s) => s.hydrated);
  const error = useGateway((s) => s.error);

  useEffect(() => {
    void hydrate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <TooltipProvider>
      <div className="flex h-full min-h-0">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar />
          {!hydrated && (
            <div className="border-b border-border px-4 py-1 text-[11px] text-muted-foreground">连接 Gateway…</div>
          )}
          {error && (
            <div className="border-b border-border px-4 py-1 text-[11px] text-error">
              后端未连接：{error} · 请先启动 FastAPI :8000
            </div>
          )}
          <main className="min-h-0 flex-1 overflow-auto p-5 md:p-6">{children}</main>
        </div>
      </div>
      <CommandPalette />
      <GlobalDialogs />
    </TooltipProvider>
  );
}

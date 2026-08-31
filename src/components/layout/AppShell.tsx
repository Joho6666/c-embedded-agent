"use client";

import type { ReactNode } from "react";
import { Group, Panel, Separator } from "react-resizable-panels";
import { TopBar } from "./TopBar";
import { Sidebar } from "./Sidebar";
import { BottomPanel } from "./BottomPanel";
import { CommandPalette } from "./CommandPalette";
import { KeyboardShortcuts } from "./KeyboardShortcuts";
import { MobileNav } from "./MobileNav";
import { useWorkspace } from "@/lib/stores/workspace";
import { PlanViewer } from "@/components/agent/PlanViewer";

export function AppShell({
  children,
  context,
}: {
  children: ReactNode;
  context?: ReactNode;
}) {
  const bottomOpen = useWorkspace((s) => s.bottomOpen);
  const plan = useWorkspace((s) => s.plan);

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-background">
      <KeyboardShortcuts />
      <CommandPalette />
      <TopBar />
      <div className="flex min-h-0 flex-1">
        <Sidebar />
        <Group orientation="vertical" className="h-full min-w-0 flex-1">
          <Panel defaultSize={bottomOpen ? "68" : "100"} minSize="30">
            <Group orientation="horizontal" className="h-full">
              <Panel defaultSize={context ? "74" : "100"} minSize="40">
                <main className="h-full overflow-auto bg-background">{children}</main>
              </Panel>
              {context !== null && (
                <>
                  <Separator className="w-px bg-border data-[separator=active]:bg-primary" />
                  <Panel defaultSize="26" minSize="16" maxSize="40" className="hidden lg:block">
                    <aside className="hidden h-full overflow-hidden border-l border-border bg-panel lg:block">
                      {context ?? <PlanViewer plan={plan} />}
                    </aside>
                  </Panel>
                </>
              )}
            </Group>
          </Panel>
          {bottomOpen && (
            <>
              <Separator className="h-px bg-border data-[separator=active]:bg-primary" />
              <Panel defaultSize="32" minSize="16" maxSize="55" className="hidden md:block">
                <BottomPanel />
              </Panel>
            </>
          )}
        </Group>
      </div>
      <MobileNav />
    </div>
  );
}

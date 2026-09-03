"use client";

import type { ReactNode } from "react";
import { Group, Panel, Separator } from "react-resizable-panels";
import { ToolBar } from "./ToolBar";
import { ActivityBar } from "./ActivityBar";
import { StatusBar } from "./StatusBar";
import { Sidebar } from "@/components/layout/Sidebar";
import { BottomPanel } from "@/components/layout/BottomPanel";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { KeyboardShortcuts } from "@/components/layout/KeyboardShortcuts";
import { MobileNav } from "@/components/layout/MobileNav";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";
import { isIdeRoute } from "@/components/layout/nav";

export function WorkbenchShell({
  children,
  pathname,
}: {
  children: ReactNode;
  pathname: string;
}) {
  const bottomOpen = useWorkspaceUI((s) => s.bottomOpen);
  const ide = isIdeRoute(pathname);
  const hideBottom =
    pathname === "/" ||
    pathname === "/start" ||
    pathname.startsWith("/projects") ||
    pathname.startsWith("/settings");

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-background">
      <KeyboardShortcuts />
      <CommandPalette />
      <ToolBar />
      <div className="flex min-h-0 flex-1">
        {ide ? <ActivityBar /> : <Sidebar />}
        <Group orientation="vertical" className="h-full min-w-0 flex-1">
          <Panel defaultSize={!hideBottom && bottomOpen ? "72" : "100"} minSize="30">
            <main className="h-full overflow-auto bg-background">{children}</main>
          </Panel>
          {!hideBottom && bottomOpen && (
            <>
              <Separator className="h-px bg-border hover:bg-primary/50 data-[separator=active]:bg-primary" />
              <Panel defaultSize="28" minSize="14" maxSize="55" className="hidden md:block">
                <BottomPanel />
              </Panel>
            </>
          )}
        </Group>
      </div>
      {ide && <StatusBar />}
      <MobileNav />
    </div>
  );
}

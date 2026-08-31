"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { PlanViewer } from "@/components/agent/PlanViewer";
import { KnowledgeDrawer } from "@/components/knowledge/KnowledgeDrawer";
import { useAgent } from "@/lib/stores/agent-store";
import { goldenPlan } from "@/lib/mock/golden-path";

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const runPlan = useAgent((s) => s.activeRun?.plan);
  const plan = runPlan ?? goldenPlan;
  const hide =
    pathname === "/agent" ||
    pathname === "/" ||
    pathname.startsWith("/projects") ||
    pathname.startsWith("/settings");
  const context = hide ? null : <PlanViewer plan={plan} />;
  return (
    <AppShell context={context}>
      <KnowledgeDrawer />
      {children}
    </AppShell>
  );
}

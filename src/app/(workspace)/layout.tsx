"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { WorkbenchShell } from "@/components/workbench/WorkbenchShell";
import { KnowledgeDrawer } from "@/components/knowledge/KnowledgeDrawer";

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <WorkbenchShell pathname={pathname}>
      <KnowledgeDrawer />
      {children}
    </WorkbenchShell>
  );
}

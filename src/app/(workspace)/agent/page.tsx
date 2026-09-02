"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";

export default function AgentRedirectPage() {
  const router = useRouter();
  const setActivity = useWorkspaceUI((s) => s.setActivity);
  const setTab = useWorkspaceUI((s) => s.setAgentPanelTab);
  useEffect(() => {
    setActivity("agent");
    setTab("plan");
    router.replace("/workspace");
  }, [router, setActivity, setTab]);
  return <div className="p-4 text-[12px] text-muted-foreground">正在打开 Workspace…</div>;
}

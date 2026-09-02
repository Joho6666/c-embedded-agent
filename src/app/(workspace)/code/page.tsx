"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";

export default function CodeRedirectPage() {
  const router = useRouter();
  const setActivity = useWorkspaceUI((s) => s.setActivity);
  useEffect(() => {
    setActivity("explorer");
    router.replace("/workspace");
  }, [router, setActivity]);
  return <div className="p-4 text-[12px] text-muted-foreground">正在打开 Workspace…</div>;
}

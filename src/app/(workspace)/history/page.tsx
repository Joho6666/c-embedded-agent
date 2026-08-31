"use client";

import Link from "next/link";
import { historyTasks } from "@/lib/mock/build";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { useAgent } from "@/lib/stores/agent-store";

export default function HistoryPage() {
  const start = useAgent((s) => s.startGoldenPath);
  return (
    <div className="p-5">
      <h1 className="text-[18px] font-semibold">历史记录</h1>
      <div className="mt-4 divide-y divide-border rounded-sm border border-border bg-panel">
        {historyTasks.map((t) => (
          <div key={t.id} className="flex items-center justify-between px-3 py-3">
            <div>
              <div className="text-[13px] font-medium">{t.title}</div>
              <div className="text-[12px] text-muted-foreground">{t.prompt}</div>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge status={t.status} />
              <Button size="sm" variant="outline" asChild>
                <Link href="/agent" onClick={() => { if (t.id === "t4") void start(); }}>
                  回放
                </Link>
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

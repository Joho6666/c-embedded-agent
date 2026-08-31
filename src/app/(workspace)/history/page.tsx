"use client";

import Link from "next/link";
import { historyTasks } from "@/lib/mock/build";
import { StatusBadge } from "@/components/common/StatusBadge";
import { useWorkspace } from "@/lib/stores/workspace";
import { Button } from "@/components/ui/button";

export default function HistoryPage() {
  const startDemo = useWorkspace((s) => s.startDemo);
  return (
    <div className="p-5">
      <h1 className="text-[18px] font-semibold">历史记录</h1>
      <p className="text-[12px] text-muted-foreground">Agent 任务时间线，可回放 STM32 LED Demo</p>
      <div className="mt-4 divide-y divide-border rounded-sm border border-border bg-panel">
        {historyTasks.map((t) => (
          <div key={t.id} className="flex items-center justify-between px-3 py-3">
            <div>
              <div className="text-[13px] font-medium">{t.title}</div>
              <div className="mt-0.5 text-[12px] text-muted-foreground">{t.prompt}</div>
              <div className="mt-1 text-[11px] text-muted-foreground">
                {t.projectName} · {t.createdAt}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge status={t.status} />
              <Button size="sm" variant="outline" asChild>
                <Link
                  href="/agent"
                  onClick={() => {
                    if (t.id === "t4") startDemo();
                  }}
                >
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

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/common/StatusBadge";
import type { HardwarePipelineResult, HardwareRunStep } from "@/types/hardware-run";
import { useAgent } from "@/lib/stores/agent-store";

function tone(status: HardwareRunStep["status"]) {
  if (status === "success") return "success";
  if (status === "failed") return "failed";
  if (status === "unavailable") return "warning";
  if (status === "running") return "running";
  return "pending";
}

export function HardwareTimeline({ result, onRetry }: { result?: HardwarePipelineResult; onRetry?: (kind: string) => void }) {
  const [open, setOpen] = useState<string | null>(null);
  const router = useRouter();
  const setPrompt = useAgent((s) => s.setPrompt);

  if (!result) {
    return <div className="text-[12px] text-muted-foreground">尚未执行 Hardware Run</div>;
  }
  if (!result.available) {
    return <div className="rounded-md border border-warning/40 bg-warning/10 p-2 text-[12px]">{result.reason ?? "Backend capability unavailable"}</div>;
  }

  return (
    <div className="space-y-2">
      {result.steps.map((s, i) => (
        <div key={s.id} className="rounded-md border border-border bg-panel p-2">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <div className="text-[11px] text-muted-foreground">Step {i + 1}</div>
              <div className="text-[13px] font-medium">{s.title}</div>
              {s.detail && <div className="truncate font-mono text-[11px] text-muted-foreground">{s.detail}</div>}
            </div>
            <StatusBadge status={tone(s.status)} label={s.status} />
          </div>
          <div className="mt-2 flex flex-wrap gap-1">
            <Button size="sm" variant="outline" onClick={() => setOpen(open === s.id ? null : s.id)}>
              {open === s.id ? "收起 Logs" : "查看 Logs"}
            </Button>
            {onRetry && (
              <Button size="sm" variant="outline" onClick={() => onRetry(s.kind)}>
                Retry
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setPrompt(`分析 Hardware Timeline 步骤 ${s.title}（${s.status}）：${s.detail ?? ""} ${s.reason ?? ""} ${s.logs ?? ""}`);
                router.push("/agent");
              }}
            >
              Ask Agent
            </Button>
          </div>
          {open === s.id && (
            <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded-sm border border-border bg-terminal p-2 text-[11px] text-muted-foreground">
              {s.logs || s.reason || "无日志"}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
}

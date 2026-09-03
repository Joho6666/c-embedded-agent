"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import type { IocConflict } from "@/types/ioc";
import { useAgent } from "@/lib/stores/agent-store";

export function ConflictBanner({ conflicts }: { conflicts: IocConflict[] }) {
  const router = useRouter();
  const setPrompt = useAgent((s) => s.setPrompt);
  if (!conflicts.length) return null;
  return (
    <div className="space-y-2">
      {conflicts.map((c) => (
        <div key={c.pin} className="rounded-md border border-warning/40 bg-warning/10 p-2 text-[12px]">
          <div className="font-medium text-warning">⚠ Pin Conflict · {c.pin}</div>
          <div className="mt-1 text-muted-foreground">{c.signals.join(" / ")}</div>
          <div className="mt-1 text-[11px]">{c.detail}</div>
          <Button
            size="sm"
            variant="outline"
            className="mt-2"
            onClick={() => {
              setPrompt(`分析引脚冲突 ${c.pin}：${c.signals.join(" vs ")}。请根据 CubeMX .ioc 给出正确 AF / GPIO 配置。`);
              router.push("/agent");
            }}
          >
            Ask Agent
          </Button>
        </div>
      ))}
    </div>
  );
}

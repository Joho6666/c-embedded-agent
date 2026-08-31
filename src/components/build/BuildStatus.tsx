import type { BuildResult } from "@/types/build";
import { MemoryUsage } from "./MemoryUsage";
import { StatusBadge } from "@/components/common/StatusBadge";

export function BuildStatus({ build }: { build: BuildResult }) {
  return (
    <div className="grid gap-3 md:grid-cols-4">
      <div className="rounded-md border border-border bg-panel p-3">
        <div className="text-[11px] text-muted-foreground">构建 #{build.number}</div>
        <StatusBadge
          className="mt-1"
          status={build.status === "success" ? "success" : build.status}
          label={build.status === "success" ? "✓ 成功" : "失败"}
        />
      </div>
      <div className="rounded-md border border-border bg-panel p-3">
        <div className="text-[11px] text-muted-foreground">耗时</div>
        <div className="font-mono text-[18px]">{build.durationSec}s</div>
      </div>
      <div className="rounded-md border border-border bg-panel p-3 md:col-span-2">
        <MemoryUsage label="Flash" used={build.flashUsedKb} total={build.flashTotalKb} />
        <div className="mt-3">
          <MemoryUsage label="RAM" used={build.ramUsedKb} total={build.ramTotalKb} />
        </div>
      </div>
    </div>
  );
}

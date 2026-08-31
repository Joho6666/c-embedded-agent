import type { BuildResult } from "@/types/build";
import { MemoryUsage } from "./MemoryUsage";
import { StatusBadge } from "@/components/common/StatusBadge";

export function BuildStatus({ build }: { build: BuildResult }) {
  return (
    <div className="grid gap-3 md:grid-cols-4">
      <div className="rounded-sm border border-border bg-panel p-3">
        <div className="text-[11px] text-muted-foreground">Build #{build.number}</div>
        <div className="mt-1 flex items-center gap-2">
          <StatusBadge
            status={build.status === "success" ? "success" : build.status}
            label={build.status === "success" ? "✓ SUCCESS" : build.status.toUpperCase()}
          />
        </div>
      </div>
      <div className="rounded-sm border border-border bg-panel p-3">
        <div className="text-[11px] text-muted-foreground">Build Time</div>
        <div className="mt-1 font-mono text-[18px]">{build.durationSec}s</div>
      </div>
      <div className="rounded-sm border border-border bg-panel p-3 md:col-span-2">
        <MemoryUsage label="Flash" used={build.flashUsedKb} total={build.flashTotalKb} />
        <div className="mt-3">
          <MemoryUsage label="RAM" used={build.ramUsedKb} total={build.ramTotalKb} />
        </div>
      </div>
      <div className="rounded-sm border border-border bg-panel p-3">
        <div className="text-[11px] text-muted-foreground">Warnings</div>
        <div className="mt-1 font-mono text-[18px] text-warning">{build.warnings}</div>
      </div>
      <div className="rounded-sm border border-border bg-panel p-3">
        <div className="text-[11px] text-muted-foreground">Errors</div>
        <div className="mt-1 font-mono text-[18px] text-error">{build.errors}</div>
      </div>
    </div>
  );
}

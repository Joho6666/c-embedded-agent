"use client";

import { BuildStatus } from "@/components/build/BuildStatus";
import { Terminal } from "@/components/terminal/Terminal";
import { latestBuild } from "@/lib/mock/build";
import { useTerminal } from "@/lib/stores/terminal-store";

export default function BuildPage() {
  const lines = useTerminal((s) => s.buildLines);
  return (
    <div className="flex h-full flex-col p-5">
      <h1 className="mb-4 text-[18px] font-semibold">构建</h1>
      <BuildStatus build={latestBuild} />
      <h2 className="mt-5 mb-2 text-[12px] text-muted-foreground">构建输出</h2>
      <div className="min-h-0 flex-1 overflow-hidden rounded-md border border-border">
        <Terminal lines={lines.length ? lines : latestBuild.output} />
      </div>
    </div>
  );
}

"use client";

import { BuildStatus } from "@/components/build/BuildStatus";
import { Terminal } from "@/components/terminal/Terminal";
import { latestBuild } from "@/lib/mock/build";
import { useWorkspace } from "@/lib/stores/workspace";

export default function BuildPage() {
  const lines = useWorkspace((s) => s.terminalLines);
  const output = lines.length > 4 ? lines : latestBuild.output;
  return (
    <div className="flex h-full flex-col p-5">
      <h1 className="mb-4 text-[18px] font-semibold">Build</h1>
      <BuildStatus build={latestBuild} />
      <h2 className="mt-5 mb-2 text-[12px] font-medium text-muted-foreground">Build Output</h2>
      <div className="min-h-0 flex-1 overflow-hidden rounded-sm border border-border">
        <Terminal lines={output} />
      </div>
    </div>
  );
}

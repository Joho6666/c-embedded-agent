"use client";

import { Button } from "@/components/ui/button";
import { useHardware } from "@/lib/stores/hardware-store";
import { useEditor } from "@/lib/stores/editor-store";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";

export function AgentSuggestedFix() {
  const run = useHardware((s) => s.hardwareRun);
  const setView = useWorkspaceUI((s) => s.setAgentView);
  const openFile = useEditor((s) => s.openFile);
  const validation = run?.validation;
  if (!validation || validation.status === "pass") return null;

  const baudMismatch = /115200|baud|clock|104167/i.test(`${validation.expected} ${validation.actual}`);
  if (!baudMismatch && validation.status !== "fail") return null;

  return (
    <div className="mx-3 mb-3 rounded-md border border-warning/40 bg-warning/10 p-3 text-[12px]">
      <div className="font-medium text-warning">Suggested Fix</div>
      <p className="mt-1 text-muted-foreground">
        {baudMismatch
          ? `USART 波特率和系统时钟可能不匹配。Expected: ${validation.expected} Actual: ${validation.actual}`
          : `${validation.expected} / ${validation.actual}`}
      </p>
      <div className="mt-2 flex gap-1">
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            openFile("/Core/Src/main.c");
            setView("code");
          }}
        >
          查看 Diff
        </Button>
      </div>
    </div>
  );
}

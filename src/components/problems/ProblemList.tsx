"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Empty } from "@/components/common/Empty";
import { useAgent } from "@/lib/stores/agent-store";
import { useEditor } from "@/lib/stores/editor-store";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";
import { problems as mockProblems } from "@/lib/mock/build";
import { cn } from "@/lib/utils";

export function ProblemList() {
  const diagnostics = useAgent((s) => s.diagnostics);
  const liveRun = useAgent((s) => s.liveRun);
  const events = useAgent((s) => s.events);
  const startGoldenPath = useAgent((s) => s.startGoldenPath);
  const openFile = useEditor((s) => s.openFile);
  const setView = useWorkspaceUI((s) => s.setAgentView);
  const router = useRouter();

  const usedLive = liveRun || events.length > 0;
  const list = usedLive
    ? diagnostics.map((d) => ({
        id: d.id,
        file: d.path,
        line: d.line,
        severity: d.severity,
        message: d.message,
        suggestion: d.suggestion,
        source: d.source,
      }))
    : mockProblems;

  const errors = list.filter((p) => p.severity === "error").length;
  const warnings = list.filter((p) => p.severity === "warning").length;

  function jump(file: string, line?: number) {
    const path = file.startsWith("/") ? file : file.includes("gpio") ? "/Core/Inc/gpio.h" : "/Core/Src/main.c";
    openFile(path, line);
    setView("code");
    router.push("/code");
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-3 py-1.5 text-[11px]">
        <span>
          问题 · <span className="text-error">{errors} 个错误</span> · <span className="text-warning">{warnings} 个警告</span>
        </span>
        <Button size="sm" variant="outline" onClick={() => void startGoldenPath()}>
          询问 Agent
        </Button>
      </div>
      <div className="flex-1 overflow-auto">
        {list.length === 0 ? (
          <Empty title="没有诊断" hint="编译通过后这里会保持为空" />
        ) : (
          list.map((p) => (
            <button
              key={p.id}
              className="block w-full border-b border-border/70 px-3 py-2 text-left hover:bg-accent/40"
              onClick={() => jump(p.file, p.line)}
            >
              <div className="flex items-center gap-2 text-[12px]">
                <span className={cn("font-medium", p.severity === "error" ? "text-error" : "text-warning")}>
                  {p.severity === "error" ? "✕" : "⚠"} {p.file}:{p.line}
                </span>
                <span>{p.message}</span>
              </div>
              {p.suggestion && <div className="mt-1 text-[11px] text-muted-foreground">Agent Fix：{p.suggestion}</div>}
            </button>
          ))
        )}
      </div>
    </div>
  );
}

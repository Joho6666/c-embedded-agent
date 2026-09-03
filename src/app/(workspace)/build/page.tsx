"use client";

import { useEffect, useState } from "react";
import { BuildStatus } from "@/components/build/BuildStatus";
import { Terminal } from "@/components/terminal/Terminal";
import { latestBuild } from "@/lib/mock/build";
import { useTerminal } from "@/lib/stores/terminal-store";
import { useLive } from "@/lib/stores/live-store";
import { useProject } from "@/lib/stores/project-store";
import { API_BASE } from "@/lib/api/client";
import { flashProject } from "@/lib/api/build";
import { Button } from "@/components/ui/button";

export default function BuildPage() {
  const lines = useTerminal((s) => s.buildLines);
  const live = useLive((s) => s.mode === "live");
  const projectId = useProject((s) => s.projectId);
  const [arts, setArts] = useState<Array<{ name: string; size: number }>>([]);
  const [flashHint, setFlashHint] = useState("");

  useEffect(() => {
    if (!live) return;
    void fetch(`${API_BASE}/api/projects/${projectId}/artifacts`)
      .then((r) => (r.ok ? r.json() : []))
      .then((rows: Array<{ name: string; size: number }>) => setArts(rows))
      .catch(() => setArts([]));
  }, [live, projectId, lines.length]);

  return (
    <div className="flex h-full flex-col p-5">
      <h1 className="mb-4 text-[18px] font-semibold">构建</h1>
      <BuildStatus build={latestBuild} />
      {live && (
        <div className="mb-3">
          <Button
            size="sm"
            variant="outline"
            onClick={async () => {
              setFlashHint("Flash 执行中…");
              const result = await flashProject(projectId);
              setFlashHint(result.success ? "Flash 成功" : `Flash 失败：${result.error ?? result.output ?? result.status ?? "无设备成功证据"}`.slice(0, 180));
            }}
          >
            Flash (OpenOCD ST-Link)
          </Button>
          {flashHint ? <span className="ml-2 text-[12px] text-muted-foreground">{flashHint}</span> : null}
        </div>
      )}
      {arts.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {arts.map((a) => (
            <a
              key={a.name}
              className="rounded-sm border border-border bg-panel px-2 py-1 font-mono text-[12px] hover:bg-accent"
              href={`${API_BASE}/api/projects/${projectId}/artifacts/${a.name}`}
            >
              下载 {a.name}
            </a>
          ))}
        </div>
      )}
      <h2 className="mt-5 mb-2 text-[12px] text-muted-foreground">构建输出</h2>
      <div className="min-h-0 flex-1 overflow-hidden rounded-md border border-border">
        <Terminal lines={lines.length ? lines : latestBuild.output} />
      </div>
    </div>
  );
}

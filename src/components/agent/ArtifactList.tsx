"use client";

import type { AgentArtifact } from "@/types/events";
import { useAgent } from "@/lib/stores/agent-store";
import { useEditor } from "@/lib/stores/editor-store";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";

const EMPTY_ARTIFACTS: AgentArtifact[] = [];

export function ArtifactList() {
  const artifacts = useAgent((s) => s.activeRun?.artifacts ?? EMPTY_ARTIFACTS);
  const events = useAgent((s) => s.events);
  const openFile = useEditor((s) => s.openFile);
  const setView = useWorkspaceUI((s) => s.setAgentView);
  const names = [
    ...new Set([
      ...artifacts.map((a) => a.name),
      ...events.flatMap((e) => e.files ?? []),
      ...(events.some((e) => e.type === "compile" && e.status === "success")
        ? ["firmware.elf", "firmware.hex", "build.log"]
        : []),
    ]),
  ];
  if (names.length === 0) return null;
  return (
    <div>
      <div className="border-b border-border px-3 py-2 text-[11px] font-medium text-muted-foreground">产物</div>
      <ul className="p-2">
        {names.map((n) => (
          <li key={n}>
            <button
              className="w-full rounded-sm px-2 py-1 text-left font-mono text-[12px] hover:bg-accent"
              onClick={() => {
                if (n.startsWith("/") || n.endsWith(".c") || n.endsWith(".h")) {
                  openFile(n.startsWith("/") ? n : n.includes("gpio.h") ? "/Core/Inc/gpio.h" : "/Core/Src/main.c");
                  setView("code");
                }
              }}
            >
              {n}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

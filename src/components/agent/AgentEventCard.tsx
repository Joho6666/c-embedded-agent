"use client";

import type { AgentEvent } from "@/types/events";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";
import { useHardware } from "@/lib/stores/hardware-store";
import { eventStatusLabel, eventTypeLabel } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export function AgentEventCard({ event }: { event: AgentEvent }) {
  const setKnowledgeId = useWorkspaceUI((s) => s.setKnowledgeId);
  const toolchain = useHardware((s) => s.context.buildTool);
  const keilCompile = event.type === "compile" && toolchain === "Keil";
  const toolName = keilCompile ? "Keil MDK" : event.tool?.name;
  const toolCmd = keilCompile ? "UV4.exe -b STM32_LED_Project.uvprojx" : event.tool?.command;

  return (
    <article className="rounded-md border border-border bg-panel p-3 hover:border-zinc-600">
      <div className="flex items-center justify-between gap-2 text-[11px]">
        <span className="font-medium tracking-wide text-muted-foreground">{eventTypeLabel[event.type] ?? event.type}</span>
        <span
          className={cn(
            event.status === "success" && "text-success",
            event.status === "failed" && "text-error",
            event.status === "running" && "text-info",
            event.status === "waiting_approval" && "text-warning",
          )}
        >
          {eventStatusLabel[event.status] ?? event.status}
        </span>
      </div>
      <h3 className="mt-1 text-[13px] font-medium">{keilCompile ? "Keil MDK 编译" : event.title}</h3>
      {event.description && event.description !== "__run_end__" && (
        <p className="mt-1 text-[12px] leading-5 text-muted-foreground">{event.description}</p>
      )}
      {event.source && (
        <button
          className="mt-1 font-mono text-[11px] text-info hover:underline"
          onClick={() => setKnowledgeId("rm0008")}
        >
          {event.source.title}
          {event.source.section ? ` · ${event.source.section}` : ""}
          {event.source.page ? ` · 第 ${event.source.page} 页` : ""}
          {event.source.score != null ? ` · ${event.source.score}` : ""}
        </button>
      )}
      {event.tool && (
        <pre className="mt-1 overflow-x-auto font-mono text-[11px] text-zinc-400">
          {toolName}
          {toolCmd ? `\n${toolCmd}` : ""}
          {event.tool.exitCode != null ? `\n退出码 ${event.tool.exitCode}` : ""}
        </pre>
      )}
      {event.files && (
        <div className="mt-1 flex flex-wrap gap-1">
          {event.files.map((f) => (
            <span key={f} className="rounded-sm bg-muted px-1.5 py-0.5 font-mono text-[11px]">
              {f}
            </span>
          ))}
        </div>
      )}
      {event.output && <pre className="mt-1 whitespace-pre-wrap font-mono text-[11px] text-zinc-400">{event.output}</pre>}
    </article>
  );
}

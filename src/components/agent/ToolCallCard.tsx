import type { ToolCall } from "@/types/agent";
import { cn } from "@/lib/utils";

export function ToolCallCard({ call }: { call: ToolCall }) {
  return (
    <div className="mt-2 rounded-sm border border-border bg-panel-2 p-2">
      <div className="flex items-center justify-between text-[11px]">
        <span className="font-medium text-info">Tool · {call.tool}</span>
        <span
          className={cn(
            call.status === "failed" && "text-error",
            call.status === "success" && "text-success",
            call.status === "running" && "text-info",
          )}
        >
          {call.status}
        </span>
      </div>
      <pre className="mt-1 overflow-x-auto font-mono text-[11px] text-zinc-300">Command: {call.command}</pre>
      {call.result && (
        <pre className="mt-1 whitespace-pre-wrap font-mono text-[11px] text-muted-foreground">{call.result}</pre>
      )}
    </div>
  );
}

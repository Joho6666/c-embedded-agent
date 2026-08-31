import type { ToolItem } from "@/types/tools";
import { StatusBadge } from "@/components/common/StatusBadge";
import { cn } from "@/lib/utils";

export function ToolCard({ tool }: { tool: ToolItem }) {
  return (
    <article className="rounded-sm border border-border bg-panel p-3">
      <div className="flex items-center justify-between">
        <h3 className="text-[13px] font-medium">{tool.name}</h3>
        <span
          className={cn(
            "size-1.5 rounded-full",
            tool.status === "connected" && "bg-success",
            tool.status === "disconnected" && "bg-zinc-600",
            tool.status === "error" && "bg-error",
          )}
        />
      </div>
      <div className="mt-2 flex items-center justify-between text-[11px] text-muted-foreground">
        <StatusBadge
          status={tool.status}
          label={
            tool.status === "connected" ? "Connected" : tool.status === "error" ? "Error" : "Disconnected"
          }
        />
        {tool.detail && <span className="font-mono">{tool.detail}</span>}
      </div>
    </article>
  );
}

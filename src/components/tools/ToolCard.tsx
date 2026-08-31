"use client";

import { toast } from "sonner";
import type { ToolItem } from "@/types/tools";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import { useTools } from "@/lib/stores/tools-store";
import { cn } from "@/lib/utils";

export function ToolCard({ tool }: { tool: ToolItem }) {
  const connect = useTools((s) => s.connect);
  const disconnect = useTools((s) => s.disconnect);
  const keil = tool.id === "keilmdk" || tool.id === "keilc51";

  return (
    <article className="rounded-md border border-border bg-panel p-3 hover:border-zinc-600">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-[13px] font-medium">{tool.name}</h3>
        <span
          className={cn(
            "size-1.5 shrink-0 rounded-full",
            tool.status === "connected" && "bg-success",
            tool.status === "disconnected" && "bg-zinc-600",
            tool.status === "error" && "bg-error",
          )}
        />
      </div>
      <div className="mt-2 flex items-center justify-between text-[11px] text-muted-foreground">
        <StatusBadge status={tool.status} />
        {tool.detail && <span className="font-mono">{tool.detail}</span>}
      </div>
      {tool.executable && (
        <div className="mt-1 truncate font-mono text-[10px] text-muted-foreground" title={tool.executable}>
          {tool.executable}
        </div>
      )}
      {keil && (
        <div className="mt-2 flex gap-1">
          {tool.status === "connected" ? (
            <Button size="sm" variant="outline" onClick={() => disconnect(tool.id)}>
              断开
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={() => {
                connect(tool.id);
                toast.success(`${tool.name} 已连接（界面 Mock，未启动编译器）`);
              }}
            >
              检测 / 连接
            </Button>
          )}
        </div>
      )}
    </article>
  );
}

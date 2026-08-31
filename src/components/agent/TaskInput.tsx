"use client";

import { FileCode, FileText, FolderPlus, Image as ImageIcon, Paperclip, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MCUSelector } from "./MCUSelector";
import { useWorkspace } from "@/lib/stores/workspace";
import { cn } from "@/lib/utils";
import type { AgentMode } from "@/types/agent";

const modes: { id: AgentMode; label: string }[] = [
  { id: "auto", label: "Auto" },
  { id: "plan", label: "Plan" },
  { id: "code", label: "Code" },
  { id: "debug", label: "Debug" },
];

const attaches = [
  { icon: FileText, label: "添加 Datasheet" },
  { icon: FileCode, label: "添加代码" },
  { icon: ImageIcon, label: "添加原理图" },
  { icon: Paperclip, label: "添加 PDF" },
  { icon: FolderPlus, label: "添加项目" },
];

export function TaskInput() {
  const prompt = useWorkspace((s) => s.prompt);
  const setPrompt = useWorkspace((s) => s.setPrompt);
  const mode = useWorkspace((s) => s.mode);
  const setMode = useWorkspace((s) => s.setMode);
  const startDemo = useWorkspace((s) => s.startDemo);
  const running = useWorkspace((s) => s.running);

  return (
    <div className="border-t border-border bg-panel p-3">
      <MCUSelector />
      <div className="mt-2 flex flex-wrap gap-1">
        {attaches.map((a) => (
          <button
            key={a.label}
            className="inline-flex items-center gap-1 rounded-sm border border-border px-1.5 py-0.5 text-[11px] text-muted-foreground hover:bg-accent"
          >
            <a.icon className="size-3" />
            {a.label}
          </button>
        ))}
      </div>
      <div className="mt-2 flex items-end gap-2">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={3}
          placeholder="描述你要实现的嵌入式功能..."
          className="min-h-[72px] flex-1 resize-none rounded-sm border border-input bg-panel-2 px-2 py-1.5 text-[13px] outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
        <div className="flex flex-col gap-1">
          <div className="flex rounded-sm border border-border">
            {modes.map((m) => (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                className={cn(
                  "px-2 py-1 text-[11px]",
                  mode === m.id ? "bg-accent text-foreground" : "text-muted-foreground",
                )}
              >
                {m.label}
              </button>
            ))}
          </div>
          <Button onClick={startDemo} disabled={running} className="h-8">
            <Play />
            Run Agent
          </Button>
        </div>
      </div>
    </div>
  );
}

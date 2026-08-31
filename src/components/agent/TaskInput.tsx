"use client";

import { useMemo, useState } from "react";
import { FileCode, FileText, FolderPlus, Image as ImageIcon, Paperclip, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MCUSelector } from "./MCUSelector";
import { useAgent } from "@/lib/stores/agent-store";
import { useHardware } from "@/lib/stores/hardware-store";
import { initialFiles } from "@/lib/mock/files";
import { knowledgeDocs } from "@/lib/mock/knowledge";
import { mcuCatalog } from "@/lib/mock/hardware";
import { cn } from "@/lib/utils";
import type { AgentMode } from "@/types/agent";

const modes: { id: AgentMode; label: string }[] = [
  { id: "auto", label: "自动" },
  { id: "plan", label: "计划" },
  { id: "code", label: "编码" },
  { id: "debug", label: "调试" },
];

const attaches = [
  { token: "@datasheet:RM0008", label: "添加 Datasheet", icon: FileText },
  { token: "@file:/Core/Src/main.c", label: "添加代码", icon: FileCode },
  { token: "@pin:PA5", label: "添加原理图", icon: ImageIcon },
  { token: "@datasheet:RM0008", label: "添加 PDF", icon: Paperclip },
  { token: "@mcu:STM32F103C8T6", label: "添加项目", icon: FolderPlus },
];

type Mention = { token: string; label: string; group: string };

export function TaskInput() {
  const prompt = useAgent((s) => s.prompt);
  const setPrompt = useAgent((s) => s.setPrompt);
  const mode = useAgent((s) => s.mode);
  const setMode = useAgent((s) => s.setMode);
  const start = useAgent((s) => s.startGoldenPath);
  const status = useAgent((s) => s.status);
  const ctx = useHardware((s) => s.context);
  const [mentionOpen, setMentionOpen] = useState(false);

  const items = useMemo<Mention[]>(
    () => [
      ...Object.keys(initialFiles).map((p) => ({ token: `@file:${p}`, label: p, group: "文件" })),
      ...knowledgeDocs.map((d) => ({ token: `@datasheet:${d.subtitle ?? d.id}`, label: d.title, group: "手册" })),
      ...mcuCatalog.map((m) => ({ token: `@mcu:${m.name}`, label: m.name, group: "MCU" })),
      ...ctx.pins.map((p) => ({ token: `@pin:${p.pin}`, label: `${p.pin} ${p.function}`, group: "引脚" })),
      { token: "@build", label: "最近构建", group: "构建" },
      { token: "@serial", label: "串口 COM3", group: "串口" },
    ],
    [ctx.pins],
  );

  const at = prompt.lastIndexOf("@");
  const query = at >= 0 ? prompt.slice(at + 1).toLowerCase() : "";
  const filtered =
    mentionOpen && at >= 0
      ? items.filter((i) => i.token.toLowerCase().includes(query) || i.label.toLowerCase().includes(query)).slice(0, 8)
      : [];

  function insert(token: string) {
    const next = at >= 0 ? `${prompt.slice(0, at)}${token} ` : `${prompt} ${token} `;
    setPrompt(next);
    setMentionOpen(false);
  }

  return (
    <div className="border-t border-border bg-panel p-3">
      <MCUSelector />
      <div className="mt-2 flex flex-wrap gap-1 text-[11px] text-muted-foreground">
        <span className="rounded-sm border border-border px-1.5 py-0.5 font-mono text-foreground">{ctx.mcu}</span>
        <span className="rounded-sm border border-border px-1.5 py-0.5">{ctx.board}</span>
        <span className="rounded-sm border border-border px-1.5 py-0.5">{ctx.framework}</span>
        <span className="rounded-sm border border-border px-1.5 py-0.5">{ctx.buildTool}</span>
        <span className="rounded-sm border border-border px-1.5 py-0.5">{ctx.debugger}</span>
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        {attaches.map((a) => (
          <button
            key={a.label}
            className="inline-flex items-center gap-1 rounded-sm border border-border px-1.5 py-0.5 text-[11px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            onClick={() => setPrompt(`${prompt} ${a.token} `)}
          >
            <a.icon className="size-3" />
            {a.label}
          </button>
        ))}
      </div>
      <div className="relative mt-2 flex items-end gap-2">
        {filtered.length > 0 && (
          <div className="absolute bottom-full mb-1 w-[min(420px,100%)] overflow-hidden rounded-md border border-border bg-popover shadow-lg">
            {filtered.map((i) => (
              <button
                key={i.token}
                className="flex w-full items-center justify-between px-2 py-1.5 text-left text-[12px] hover:bg-accent"
                onMouseDown={(e) => {
                  e.preventDefault();
                  insert(i.token);
                }}
              >
                <span className="font-mono">{i.token}</span>
                <span className="text-[10px] text-muted-foreground">{i.group}</span>
              </button>
            ))}
          </div>
        )}
        <textarea
          value={prompt}
          onChange={(e) => {
            setPrompt(e.target.value);
            setMentionOpen(e.target.value.includes("@"));
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape") setMentionOpen(false);
          }}
          rows={3}
          placeholder="描述你要实现的嵌入式功能… 输入 @ 引用文件 / 手册 / MCU / 引脚"
          className="min-h-[72px] flex-1 resize-none rounded-sm border border-input bg-panel-2 px-2 py-1.5 text-[13px] outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
        <div className="flex flex-col gap-1">
          <div className="flex overflow-hidden rounded-sm border border-border">
            {modes.map((m) => (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                className={cn("px-2 py-1 text-[11px]", mode === m.id ? "bg-accent text-foreground" : "text-muted-foreground")}
              >
                {m.label}
              </button>
            ))}
          </div>
          <Button onClick={() => void start()} disabled={status === "working" || status === "waiting_approval"} className="h-8">
            <Play />
            运行 Agent
          </Button>
        </div>
      </div>
    </div>
  );
}

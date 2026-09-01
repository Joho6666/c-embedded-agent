"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import { navItems } from "./nav";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";
import { useAgent } from "@/lib/stores/agent-store";
import { useEditor } from "@/lib/stores/editor-store";
import { mcuCatalog } from "@/lib/mock/hardware";
import { useHardware } from "@/lib/stores/hardware-store";

export function CommandPalette() {
  const open = useWorkspaceUI((s) => s.commandOpen);
  const setOpen = useWorkspaceUI((s) => s.setCommandOpen);
  const startGoldenPath = useAgent((s) => s.startGoldenPath);
  const stopRun = useAgent((s) => s.stopRun);
  const saveFile = useEditor((s) => s.saveFile);
  const acceptAll = useEditor((s) => s.acceptAll);
  const undo = useEditor((s) => s.undoLastAiChange);
  const approve = useAgent((s) => s.approve);
  const patches = useEditor((s) => s.patches);
  const setContext = useHardware((s) => s.setContext);
  const router = useRouter();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(!open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  if (!open) return null;

  const go = (href: string) => {
    router.push(href);
    setOpen(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-[18vh]" onClick={() => setOpen(false)}>
      <Command className="w-[520px] overflow-hidden rounded-md border border-border bg-popover shadow-xl" onClick={(e) => e.stopPropagation()}>
        <Command.Input
          placeholder="搜索页面与操作…"
          className="h-10 w-full border-b border-border bg-transparent px-3 text-[13px] outline-none"
        />
        <Command.List className="max-h-72 overflow-auto p-1">
          <Command.Empty className="px-3 py-6 text-center text-[12px] text-muted-foreground">无匹配</Command.Empty>
          <Command.Group heading="操作" className="px-1 py-1 text-[10px] text-muted-foreground">
            {[
              { id: "demo", label: "运行 STM32 LED 演示", run: () => { void startGoldenPath(); go("/agent"); } },
              { id: "stop", label: "停止 Agent", run: () => { void stopRun(); setOpen(false); } },
              { id: "save", label: "保存当前文件", run: () => { saveFile(); setOpen(false); } },
              {
                id: "accept",
                label: "接受待处理补丁",
                run: () => {
                  const p = patches.find((x) => x.status === "pending");
                  acceptAll();
                  if (p?.approvalId) void approve("approved", p.approvalId);
                  setOpen(false);
                },
              },
              { id: "undo", label: "撤销上次 AI 修改", run: () => { undo(); setOpen(false); } },
            ].map((a) => (
              <Command.Item
                key={a.id}
                value={a.label}
                onSelect={a.run}
                className="flex cursor-pointer rounded-sm px-2 py-1.5 text-[12px] text-foreground data-[selected=true]:bg-accent"
              >
                {a.label}
              </Command.Item>
            ))}
          </Command.Group>
          <Command.Group heading="页面" className="px-1 py-1 text-[10px] text-muted-foreground">
            {[
              ...navItems.map((n) => ({ href: n.href, label: n.label })),
              { href: "/build", label: "构建" },
              { href: "/problems", label: "问题" },
              { href: "/serial", label: "串口" },
              { href: "/debug", label: "调试" },
              { href: "/mcu/pins", label: "引脚图" },
              { href: "/projects/new", label: "导入 CubeMX" },
            ].map((n) => (
              <Command.Item
                key={n.href}
                value={n.label}
                onSelect={() => go(n.href)}
                className="flex cursor-pointer rounded-sm px-2 py-1.5 text-[12px] text-foreground data-[selected=true]:bg-accent"
              >
                {n.label}
              </Command.Item>
            ))}
          </Command.Group>
          <Command.Group heading="MCU" className="px-1 py-1 text-[10px] text-muted-foreground">
            {mcuCatalog.map((m) => (
              <Command.Item
                key={m.id}
                value={`mcu ${m.name}`}
                onSelect={() => {
                  setContext({ mcu: m.name, core: m.core, package: m.package, flashKb: m.flashKb, ramKb: m.ramKb, clock: m.frequency });
                  setOpen(false);
                }}
                className="flex cursor-pointer rounded-sm px-2 py-1.5 font-mono text-[12px] data-[selected=true]:bg-accent"
              >
                {m.name}
              </Command.Item>
            ))}
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  );
}

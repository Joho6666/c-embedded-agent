"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import { navItems } from "./nav";
import { useWorkspace } from "@/lib/stores/workspace";

export function CommandPalette() {
  const open = useWorkspace((s) => s.commandOpen);
  const setOpen = useWorkspace((s) => s.setCommandOpen);
  const startDemo = useWorkspace((s) => s.startDemo);
  const runBuild = useWorkspace((s) => s.runBuild);
  const runFlash = useWorkspace((s) => s.runFlash);
  const router = useRouter();
  const [q, setQ] = useState("");

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

  const actions = useMemo(
    () => [
      { id: "demo", label: "运行 STM32 LED Demo", run: () => { startDemo(); router.push("/agent"); } },
      { id: "build", label: "Build 当前工程", run: runBuild },
      { id: "flash", label: "Flash 固件", run: runFlash },
    ],
    [router, runBuild, runFlash, startDemo],
  );

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-[18vh]" onClick={() => setOpen(false)}>
      <Command
        className="w-[520px] overflow-hidden rounded-md border border-border bg-popover shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <Command.Input
          value={q}
          onValueChange={setQ}
          placeholder="Agent Command · 搜索页面与操作"
          className="h-10 w-full border-b border-border bg-transparent px-3 text-[13px] outline-none"
        />
        <Command.List className="max-h-72 overflow-auto p-1">
          <Command.Empty className="px-3 py-6 text-center text-[12px] text-muted-foreground">
            无匹配
          </Command.Empty>
          <Command.Group heading="操作" className="px-1 py-1 text-[10px] text-muted-foreground">
            {actions.map((a) => (
              <Command.Item
                key={a.id}
                value={a.label}
                onSelect={() => {
                  a.run();
                  setOpen(false);
                }}
                className="flex cursor-pointer items-center rounded-sm px-2 py-1.5 text-[12px] text-foreground data-[selected=true]:bg-accent"
              >
                {a.label}
              </Command.Item>
            ))}
          </Command.Group>
          <Command.Group heading="页面" className="px-1 py-1 text-[10px] text-muted-foreground">
            {[
              ...navItems.map((n) => ({ href: n.href, label: n.label })),
              { href: "/projects/new", label: "新建项目" },
              { href: "/mcu/pins", label: "Pin Configuration" },
              { href: "/build", label: "Build" },
              { href: "/problems", label: "Problems" },
              { href: "/serial", label: "Serial Monitor" },
              { href: "/debug", label: "Debug" },
              { href: "/code", label: "Code Editor" },
            ].map((n) => (
              <Command.Item
                key={n.href}
                value={n.label}
                onSelect={() => {
                  router.push(n.href);
                  setOpen(false);
                }}
                className="flex cursor-pointer items-center rounded-sm px-2 py-1.5 text-[12px] text-foreground data-[selected=true]:bg-accent"
              >
                {n.label}
              </Command.Item>
            ))}
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  );
}

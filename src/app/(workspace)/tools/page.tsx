"use client";

import { useEffect, useState } from "react";
import { ToolCard } from "@/components/tools/ToolCard";
import { useTools } from "@/lib/stores/tools-store";
import { toolGroupLabel } from "@/lib/i18n";
import { API_BASE } from "@/lib/api/client";
import { useLive } from "@/lib/stores/live-store";
import type { ToolItem } from "@/types/tools";

const groups: ToolItem["group"][] = [
  "Generator",
  "Compiler",
  "Code Intelligence",
  "Static Analysis",
  "Testing",
  "Hardware",
  "Serial",
  "Git",
];

export default function ToolsPage() {
  const items = useTools((s) => s.items);
  const setStatus = useTools((s) => s.setStatus);
  const mode = useLive((s) => s.mode);
  const [hint, setHint] = useState("");

  useEffect(() => {
    if (mode !== "live") return;
    void fetch(`${API_BASE}/api/tools/status`)
      .then((r) => r.json())
      .then((rows: Array<{ id: string; installed: boolean; version?: string | null; name: string }>) => {
        const map: Record<string, string> = {
          "arm-gcc": "armgcc",
          make: "armgcc",
          clangd: "clangd",
          cppcheck: "cppcheck",
          openocd: "openocd",
          git: "git",
        };
        for (const row of rows) {
          const id = map[row.id];
          if (!id) continue;
          setStatus(id, row.installed ? "connected" : "disconnected", {
            detail: row.installed ? row.version ?? "ok" : "未安装",
          });
        }
        const gcc = rows.find((x) => x.id === "arm-gcc");
        setHint(gcc?.installed ? "LIVE：已检测到 ARM GCC" : "LIVE：未检测到 arm-none-eabi-gcc，不会伪装编译成功");
      })
      .catch(() => setHint("无法读取后端工具状态"));
  }, [mode, setStatus]);

  return (
    <div className="p-5">
      <h1 className="text-[18px] font-semibold">工具</h1>
      <p className="text-[12px] text-muted-foreground">
        {hint || "Keil MDK 为界面连通。ESP32 / C51 / Keil 真编译：即将推出。"}
      </p>
      {groups.map((g) => (
        <section key={g} className="mt-5">
          <h2 className="mb-2 text-[12px] font-medium text-muted-foreground">{toolGroupLabel[g] ?? g}</h2>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {items
              .filter((t) => t.group === g)
              .map((t) => (
                <ToolCard key={t.id} tool={t} />
              ))}
          </div>
        </section>
      ))}
    </div>
  );
}

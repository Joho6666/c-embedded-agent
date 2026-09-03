"use client";

import type { PinConfig } from "@/types/mcu";
import { useHardware } from "@/lib/stores/hardware-store";
import { cn } from "@/lib/utils";

export function PinMap({ pins }: { pins: PinConfig[] }) {
  const conflict = useHardware((s) => s.conflict);
  const left = pins.filter((p) => p.side === "left");
  const right = pins.filter((p) => p.side === "right");
  const top = pins.filter((p) => p.side === "top");
  const bottom = pins.filter((p) => p.side === "bottom");

  function hi(name: string) {
    return name === "PA5" || name === conflict?.pin;
  }

  return (
    <div>
      <h2 className="mb-3 text-[12px] text-muted-foreground">引脚配置</h2>
      <div className="grid items-center gap-3 lg:grid-cols-[1fr_220px_1fr]">
        <div className="space-y-1">
          {(left.length ? left : pins.slice(0, Math.ceil(pins.length / 2))).map((p) => (
            <PinRow key={p.name} pin={p} align="right" hot={hi(p.name)} />
          ))}
        </div>
        <div className="mx-auto flex aspect-square w-[220px] flex-col items-center justify-between rounded-sm border border-border bg-panel-2 p-3">
          <div className="flex flex-wrap justify-center gap-1">
            {top.map((p) => (
              <span key={p.name} className={cn("font-mono text-[9px]", hi(p.name) ? "text-warning" : "text-muted-foreground")}>
                {p.name}
              </span>
            ))}
          </div>
          <div className="text-center">
            <div className="font-mono text-[13px] font-semibold">LQFP</div>
            <div className="text-[10px] text-muted-foreground">PA5 LED · PA9 USART</div>
          </div>
          <div className="flex flex-wrap justify-center gap-1">
            {bottom.map((p) => (
              <span key={p.name} className={cn("font-mono text-[9px]", hi(p.name) ? "text-warning" : "text-muted-foreground")}>
                {p.name}
              </span>
            ))}
          </div>
        </div>
        <div className="space-y-1">
          {(right.length ? right : pins.slice(Math.ceil(pins.length / 2))).map((p) => (
            <PinRow key={p.name} pin={p} align="left" hot={hi(p.name)} />
          ))}
        </div>
      </div>
      <div className="mt-4 overflow-auto rounded-sm border border-border">
        <table className="w-full text-left text-[12px]">
          <thead className="bg-muted text-[11px] text-muted-foreground">
            <tr>
              <th className="px-3 py-1.5">引脚</th>
              <th className="px-3 py-1.5">功能</th>
              <th className="px-3 py-1.5">分配</th>
              <th className="px-3 py-1.5">备注</th>
            </tr>
          </thead>
          <tbody>
            {pins.map((p) => (
              <tr key={p.name} className={cn("border-t border-border", hi(p.name) && "bg-warning/10")}>
                <td className="px-3 py-1.5 font-mono">{p.name}</td>
                <td className="px-3 py-1.5 text-muted-foreground">{p.functions.join(" / ")}</td>
                <td className="px-3 py-1.5">{p.assigned ?? "—"}</td>
                <td className="px-3 py-1.5">{p.note ?? (conflict?.pin === p.name ? "冲突" : "")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PinRow({ pin, align, hot }: { pin: PinConfig; align: "left" | "right"; hot?: boolean }) {
  return (
    <div className={cn("flex items-center gap-2 text-[11px]", align === "right" && "justify-end")}>
      {align === "right" && <span className={cn("truncate", hot && "text-warning")}>{pin.assigned ?? pin.functions[0]}</span>}
      <span className={cn("inline-flex min-w-12 justify-center rounded-sm border bg-panel px-1 font-mono", hot ? "border-warning text-warning" : "border-border")}>
        {pin.name}
      </span>
      {align === "left" && (
        <span className={cn("truncate", hot && "text-warning")}>
          {pin.assigned ?? pin.functions[0]}
          {pin.note ? ` · ${pin.note}` : ""}
        </span>
      )}
    </div>
  );
}

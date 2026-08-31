"use client";

import { useHardware } from "@/lib/stores/hardware-store";

export function HardwareContextPanel() {
  const ctx = useHardware((s) => s.context);
  const conflict = useHardware((s) => s.conflict);
  const rows: [string, string][] = [
    ["厂商", ctx.vendor],
    ["MCU", ctx.mcu],
    ["开发板", ctx.board],
    ["内核", ctx.core],
    ["框架", ctx.framework],
    ["时钟", ctx.clock],
    ["调试器", ctx.debugger],
    ["串口", `${ctx.serialPort} @ ${ctx.serialBaud}`],
    ["工具链", ctx.buildTool],
    ["工程生成", ctx.projectGenerator],
  ];
  return (
    <div>
      <div className="border-b border-border px-3 py-2 text-[11px] font-medium text-muted-foreground">硬件上下文</div>
      <dl className="space-y-1.5 p-3 text-[12px]">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-2">
            <dt className="text-muted-foreground">{k}</dt>
            <dd className="text-right font-mono">{v}</dd>
          </div>
        ))}
      </dl>
      {conflict && (
        <div className="mx-3 mb-3 rounded-sm border border-warning/40 bg-warning/10 p-2 text-[11px]">
          ⚠ 引脚冲突 {conflict.pin}
          <div>当前：{conflict.current.function}</div>
          <div>请求：{conflict.requested.function}</div>
        </div>
      )}
    </div>
  );
}

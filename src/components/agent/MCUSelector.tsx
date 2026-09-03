"use client";

import { mcuCatalog } from "@/lib/mock/hardware";
import { useHardware } from "@/lib/stores/hardware-store";

const fields = [
  { key: "platform", label: "平台", options: ["STM32", "ESP32", "8051", "AVR", "RP2040", "Linux"] },
  { key: "framework", label: "框架", options: ["HAL", "LL", "CMSIS", "Bare Metal", "ESP-IDF"] },
  { key: "rtos", label: "RTOS", options: ["None", "FreeRTOS", "RT-Thread"] },
  { key: "buildTool", label: "工具链", options: ["ARM GCC", "Keil", "PlatformIO", "ESP-IDF"] },
] as const;

export function MCUSelector({ compact = false }: { compact?: boolean }) {
  const ctx = useHardware((s) => s.context);
  const setContext = useHardware((s) => s.setContext);

  return (
    <div className={compact ? "flex flex-wrap gap-1" : "grid grid-cols-2 gap-2 md:grid-cols-5"}>
      <label className="flex flex-col gap-1 text-[10px] text-muted-foreground">
        MCU
        <select
          className="h-7 rounded-sm border border-input bg-panel-2 px-1.5 text-[12px] text-foreground"
          value={ctx.mcu}
          onChange={(e) => {
            const m = mcuCatalog.find((x) => x.name === e.target.value);
            setContext({
              mcu: e.target.value,
              core: m?.core ?? ctx.core,
              package: m?.package ?? ctx.package,
              flashKb: m?.flashKb ?? ctx.flashKb,
              ramKb: m?.ramKb ?? ctx.ramKb,
              clock: m?.frequency ?? ctx.clock,
              platform: m?.family.includes("ESP") ? "ESP32" : m?.family.includes("8051") ? "8051" : ctx.platform,
            });
          }}
        >
          {mcuCatalog.map((m) => (
            <option key={m.id}>{m.name}</option>
          ))}
        </select>
      </label>
      {fields.map((f) => (
        <label key={f.key} className="flex flex-col gap-1 text-[10px] text-muted-foreground">
          {f.label}
          <select
            className="h-7 rounded-sm border border-input bg-panel-2 px-1.5 text-[12px] text-foreground"
            value={ctx[f.key]}
            onChange={(e) => setContext({ [f.key]: e.target.value })}
          >
            {f.options.map((o) => (
              <option key={o} value={o}>
                {o === "None" ? "无" : o === "Bare Metal" ? "裸机" : o}
              </option>
            ))}
          </select>
        </label>
      ))}
    </div>
  );
}

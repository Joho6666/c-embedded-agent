"use client";

import { useWorkspace } from "@/lib/stores/workspace";

const fields = [
  { key: "platform", label: "Platform", options: ["STM32", "ESP32", "8051", "AVR", "RP2040", "Linux"] },
  {
    key: "mcu",
    label: "MCU",
    options: ["STM32F103C8T6", "STM32F407VGT6", "STM32H743", "ESP32-S3", "STC89C52RC"],
  },
  { key: "framework", label: "Framework", options: ["HAL", "LL", "CMSIS", "Bare Metal", "ESP-IDF", "Arduino", "FreeRTOS"] },
  { key: "rtos", label: "RTOS", options: ["None", "FreeRTOS", "RT-Thread", "Zephyr"] },
  { key: "buildTool", label: "Build", options: ["ARM GCC", "Keil", "PlatformIO", "ESP-IDF"] },
] as const;

export function MCUSelector() {
  const values = useWorkspace((s) => ({
    platform: s.platform,
    mcu: s.mcu,
    framework: s.framework,
    rtos: s.rtos,
    buildTool: s.buildTool,
  }));
  const setSelectors = useWorkspace((s) => s.setSelectors);

  return (
    <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
      {fields.map((f) => (
        <label key={f.key} className="flex flex-col gap-1 text-[10px] text-muted-foreground">
          {f.label}
          <select
            className="h-7 rounded-sm border border-input bg-panel-2 px-1.5 text-[12px] text-foreground outline-none"
            value={values[f.key]}
            onChange={(e) => setSelectors({ [f.key]: e.target.value })}
          >
            {f.options.map((o) => (
              <option key={o}>{o}</option>
            ))}
          </select>
        </label>
      ))}
    </div>
  );
}

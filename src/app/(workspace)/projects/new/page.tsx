"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { mcuCatalog } from "@/lib/mock/hardware";
import { useHardware } from "@/lib/stores/hardware-store";
import { useAgent } from "@/lib/stores/agent-store";
import { cn } from "@/lib/utils";
import type { PlatformId } from "@/types/project";

const platforms: PlatformId[] = ["STM32", "ESP32", "8051", "AVR", "RP2040", "Linux"];

export default function NewProjectPage() {
  const router = useRouter();
  const setContext = useHardware((s) => s.setContext);
  const start = useAgent((s) => s.startGoldenPath);
  const [step, setStep] = useState(1);
  const [platform, setPlatform] = useState<PlatformId>("STM32");
  const [mcu, setMcu] = useState("STM32F103C8T6");
  const [framework, setFramework] = useState("HAL");
  const [toolchain, setToolchain] = useState("ARM GCC");

  return (
    <div className="mx-auto max-w-2xl p-6">
      <div className="text-[11px] text-muted-foreground">新建项目 · 第 {step} / 4 步</div>
      <h1 className="text-[18px] font-semibold">创建嵌入式工程</h1>
      <p className="mt-2 text-[13px] text-muted-foreground">
        {step === 1 && "选择平台"}
        {step === 2 && "选择 MCU"}
        {step === 3 && "选择开发框架"}
        {step === 4 && "选择工具链"}
      </p>
      {step === 1 && (
        <div className="mt-4 grid grid-cols-3 gap-2">
          {platforms.map((p) => (
            <button key={p} onClick={() => setPlatform(p)} className={cn("rounded-sm border px-3 py-4", platform === p ? "border-primary bg-accent" : "border-border")}>
              {p}
            </button>
          ))}
        </div>
      )}
      {step === 2 && (
        <div className="mt-4 space-y-1">
          {mcuCatalog.map((m) => (
            <button key={m.id} onClick={() => setMcu(m.name)} className={cn("flex w-full justify-between rounded-sm border px-3 py-2", mcu === m.name ? "border-primary bg-accent" : "border-border")}>
              <span className="font-mono">{m.name}</span>
              <span className="text-[11px] text-muted-foreground">{m.core}</span>
            </button>
          ))}
        </div>
      )}
      {step === 3 && (
        <div className="mt-4 grid grid-cols-2 gap-2">
          {["HAL", "LL", "CMSIS", "Bare Metal"].map((f) => (
            <button key={f} onClick={() => setFramework(f)} className={cn("rounded-sm border px-3 py-3", framework === f ? "border-primary bg-accent" : "border-border")}>
              {f === "Bare Metal" ? "裸机" : f}
            </button>
          ))}
        </div>
      )}
      {step === 4 && (
        <div className="mt-4 grid grid-cols-2 gap-2">
          {["ARM GCC", "Keil", "PlatformIO"].map((t) => (
            <button key={t} onClick={() => setToolchain(t)} className={cn("rounded-sm border px-3 py-3", toolchain === t ? "border-primary bg-accent" : "border-border")}>
              {t}
            </button>
          ))}
        </div>
      )}
      <div className="mt-6 flex justify-between">
        <Button variant="outline" disabled={step === 1} onClick={() => setStep((s) => s - 1)}>
          上一步
        </Button>
        {step < 4 ? (
          <Button onClick={() => setStep((s) => s + 1)}>下一步</Button>
        ) : (
          <Button
            onClick={() => {
              setContext({ platform, mcu, framework, buildTool: toolchain });
              void start();
              router.push("/agent");
            }}
          >
            创建并进入 Agent
          </Button>
        )}
      </div>
    </div>
  );
}

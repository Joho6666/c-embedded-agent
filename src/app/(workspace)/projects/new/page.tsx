"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { mcuCatalog } from "@/lib/mock/mcu";
import { useWorkspace } from "@/lib/stores/workspace";
import { cn } from "@/lib/utils";
import type { PlatformId } from "@/types/project";

const platforms: PlatformId[] = ["STM32", "ESP32", "8051", "AVR", "RP2040", "Linux"];
const frameworks = ["HAL", "LL", "CMSIS", "Bare Metal", "ESP-IDF", "Arduino", "FreeRTOS"];
const toolchains = ["ARM GCC", "Keil", "PlatformIO", "ESP-IDF"];

export default function NewProjectPage() {
  const router = useRouter();
  const setSelectors = useWorkspace((s) => s.setSelectors);
  const startDemo = useWorkspace((s) => s.startDemo);
  const [step, setStep] = useState(1);
  const [platform, setPlatform] = useState<PlatformId>("STM32");
  const [q, setQ] = useState("");
  const [mcu, setMcu] = useState("STM32F103C8T6");
  const [framework, setFramework] = useState("HAL");
  const [toolchain, setToolchain] = useState("ARM GCC");

  const mcus = mcuCatalog.filter((m) => m.name.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="mx-auto max-w-2xl p-6">
      <div className="text-[11px] text-muted-foreground">新建项目 · Step {step} / 4</div>
      <h1 className="mt-1 text-[18px] font-semibold">创建嵌入式工程</h1>
      <div className="mt-3 flex gap-1">
        {[1, 2, 3, 4].map((n) => (
          <div key={n} className={cn("h-1 flex-1 rounded-sm", n <= step ? "bg-primary" : "bg-muted")} />
        ))}
      </div>

      {step === 1 && (
        <section className="mt-6">
          <h2 className="text-[13px] font-medium">选择平台</h2>
          <div className="mt-3 grid grid-cols-3 gap-2">
            {platforms.map((p) => (
              <button
                key={p}
                onClick={() => setPlatform(p)}
                className={cn(
                  "rounded-sm border px-3 py-4 text-[13px]",
                  platform === p ? "border-primary bg-accent" : "border-border bg-panel",
                )}
              >
                {p}
              </button>
            ))}
          </div>
        </section>
      )}

      {step === 2 && (
        <section className="mt-6">
          <h2 className="text-[13px] font-medium">选择 MCU</h2>
          <Input className="mt-3" placeholder="搜索 STM32F103C8T6" value={q} onChange={(e) => setQ(e.target.value)} />
          <div className="mt-3 space-y-1">
            {mcus.map((m) => (
              <button
                key={m.id}
                onClick={() => setMcu(m.name)}
                className={cn(
                  "flex w-full items-center justify-between rounded-sm border px-3 py-2 text-left text-[13px]",
                  mcu === m.name ? "border-primary bg-accent" : "border-border bg-panel",
                )}
              >
                <span className="font-mono">{m.name}</span>
                <span className="text-[11px] text-muted-foreground">{m.core}</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {step === 3 && (
        <section className="mt-6">
          <h2 className="text-[13px] font-medium">开发框架</h2>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {frameworks.map((f) => (
              <button
                key={f}
                onClick={() => setFramework(f)}
                className={cn(
                  "rounded-sm border px-3 py-3 text-[13px]",
                  framework === f ? "border-primary bg-accent" : "border-border bg-panel",
                )}
              >
                {f}
              </button>
            ))}
          </div>
        </section>
      )}

      {step === 4 && (
        <section className="mt-6">
          <h2 className="text-[13px] font-medium">工具链</h2>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {toolchains.map((t) => (
              <button
                key={t}
                onClick={() => setToolchain(t)}
                className={cn(
                  "rounded-sm border px-3 py-3 text-[13px]",
                  toolchain === t ? "border-primary bg-accent" : "border-border bg-panel",
                )}
              >
                {t}
              </button>
            ))}
          </div>
        </section>
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
              setSelectors({ platform, mcu, framework, buildTool: toolchain });
              startDemo();
              router.push("/agent");
            }}
          >
            创建并进入 Agent Workspace
          </Button>
        )}
      </div>
    </div>
  );
}

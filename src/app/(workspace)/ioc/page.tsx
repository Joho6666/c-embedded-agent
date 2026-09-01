"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ClockTree } from "@/components/ioc/ClockTree";
import { ConflictBanner } from "@/components/ioc/ConflictBanner";
import { IocPinout } from "@/components/ioc/IocPinout";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";
import { getProjectIoc } from "@/lib/api/ioc";
import { useHardware } from "@/lib/stores/hardware-store";
import { useProject } from "@/lib/stores/project-store";
import { useAgent } from "@/lib/stores/agent-store";
import { useLive } from "@/lib/stores/live-store";

export default function IocPage() {
  const ioc = useHardware((s) => s.ioc);
  const setIoc = useHardware((s) => s.setIoc);
  const projectId = useProject((s) => s.projectId);
  const mode = useLive((s) => s.mode);
  const setPrompt = useAgent((s) => s.setPrompt);
  const router = useRouter();

  useEffect(() => {
    if (ioc || mode !== "live") return;
    void getProjectIoc(projectId).then((r) => {
      if (r.available && r.analysis) setIoc(r.analysis);
    });
  }, [ioc, mode, projectId, setIoc]);

  if (!ioc) {
    return (
      <div className="p-5">
        <h1 className="text-[18px] font-semibold">IOC Analysis</h1>
        <p className="mt-1 text-[12px] text-muted-foreground">导入 CubeMX .ioc 后在此查看 MCU / Clock / Pinout。</p>
        <div className="mt-4">
          <CapabilityBanner reason="尚未导入 .ioc。请从「创建项目」导入 CubeMX。" kind="empty" />
        </div>
        <Button className="mt-3" variant="outline" onClick={() => router.push("/projects/new")}>
          导入 CubeMX
        </Button>
      </div>
    );
  }

  const highlight = ioc.conflicts.map((c) => c.pin);

  return (
    <div className="flex h-full min-h-0">
      <aside className="w-[240px] shrink-0 overflow-auto border-r border-border p-3">
        <div className="text-[11px] text-muted-foreground">Project Configuration</div>
        <h1 className="mt-1 text-[16px] font-semibold">IOC Analysis</h1>
        <dl className="mt-3 space-y-1.5 text-[12px]">
          {[
            ["MCU", ioc.mcu ?? "—"],
            ["Family", ioc.family ?? "—"],
            ["Board", ioc.board ?? "—"],
            ["Clock", ioc.clock?.sysclkHz ? `${Math.round(ioc.clock.sysclkHz / 1e6)} MHz` : "—"],
            ["HSE", ioc.clock?.hseHz ? `${Math.round(ioc.clock.hseHz / 1e6)} MHz` : "—"],
            ["FreeRTOS", ioc.freertos ? "yes" : "no"],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between gap-2">
              <dt className="text-muted-foreground">{k}</dt>
              <dd className="font-mono">{v}</dd>
            </div>
          ))}
        </dl>
        <div className="mt-4">
          <ClockTree clock={ioc.clock} />
        </div>
      </aside>
      <main className="min-w-0 flex-1 overflow-auto p-3">
        <div className="mb-2 text-[11px] text-muted-foreground">MCU Pinout</div>
        <IocPinout pins={ioc.pins} highlight={highlight} />
      </main>
      <aside className="w-[280px] shrink-0 overflow-auto border-l border-border p-3">
        <div className="text-[11px] text-muted-foreground">Agent Analysis</div>
        <div className="mt-2 space-y-2 text-[12px]">
          <div>USART {ioc.usart.map((p) => p.name).join(", ") || "—"}</div>
          <div>TIM {ioc.tim.map((p) => p.name).join(", ") || "—"}</div>
          <div>PWM {ioc.pwm.map((p) => p.name).join(", ") || "—"}</div>
          <div>DMA {ioc.dma.map((p) => p.name).join(", ") || "—"}</div>
          <div>NVIC {ioc.nvic.slice(0, 6).join(", ") || "—"}</div>
        </div>
        <div className="mt-4">
          <ConflictBanner conflicts={ioc.conflicts} />
        </div>
        <Button
          size="sm"
          className="mt-3"
          variant="outline"
          onClick={() => {
            setPrompt(
              `根据已导入的 CubeMX .ioc（${ioc.mcu} ${ioc.board ?? ""} ${ioc.clock?.sysclkHz ? Math.round(ioc.clock.sysclkHz / 1e6) + "MHz" : ""}）分析工程配置与引脚映射。`,
            );
            router.push("/agent");
          }}
        >
          Ask Agent
        </Button>
      </aside>
    </div>
  );
}

"use client";

import { useState } from "react";
import Link from "next/link";
import { MCUInfo } from "@/components/mcu/MCUInfo";
import { MCUSelector } from "@/components/agent/MCUSelector";
import { ClockTree } from "@/components/ioc/ClockTree";
import { IocPinout } from "@/components/ioc/IocPinout";
import { currentMcu, mcuCatalog } from "@/lib/mock/hardware";
import { useHardware } from "@/lib/stores/hardware-store";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const tabs = ["Overview", "Pinout", "Clock", "Memory", "Peripherals", "Interrupts", "Alternate Functions", "Board"] as const;

export default function McuPage() {
  const ctx = useHardware((s) => s.context);
  const ioc = useHardware((s) => s.ioc);
  const mcu = mcuCatalog.find((m) => m.name === ctx.mcu) ?? currentMcu;
  const [tab, setTab] = useState<(typeof tabs)[number]>("Overview");
  const sources = ctx.evidence?.length
    ? ctx.evidence
    : [
        { kind: "datasheet" as const, label: "STM32F103 Datasheet" },
        { kind: "rm0008" as const, label: "RM0008" },
        { kind: "board" as const, label: "Board Profile" },
        ...(ioc ? [{ kind: "ioc" as const, label: `CubeMX .ioc (${ioc.filename})` }] : []),
      ];

  return (
    <div className="p-5">
      <div className="mb-4 flex justify-between">
        <div>
          <h1 className="text-[18px] font-semibold">MCU Intelligence</h1>
          <p className="text-[12px] text-muted-foreground">Agent 当前依据 · {ctx.mcu}</p>
        </div>
        <div className="flex gap-1">
          <Button variant="outline" asChild>
            <Link href="/mcu/pins">Pin Configuration</Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/ioc">IOC</Link>
          </Button>
        </div>
      </div>
      <div className="mb-4">
        <MCUSelector />
      </div>
      <div className="mb-4 rounded-md border border-border bg-panel p-3">
        <div className="text-[11px] text-muted-foreground">Agent 当前依据</div>
        <div className="mt-1 font-mono text-[13px]">{ctx.mcu}</div>
        <div className="mt-2 flex flex-wrap gap-1">
          {sources.map((s) => (
            <span key={s.label} className="rounded-sm border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">
              {s.label}
            </span>
          ))}
        </div>
      </div>
      <div className="mb-3 flex flex-wrap gap-1">
        {tabs.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={cn("rounded-sm px-2 py-1 text-[12px]", tab === t ? "bg-accent" : "text-muted-foreground")}
          >
            {t}
          </button>
        ))}
      </div>
      {tab === "Overview" && <MCUInfo mcu={{ ...mcu, name: ctx.mcu }} />}
      {tab === "Pinout" && (
        <div>
          {ioc ? <IocPinout pins={ioc.pins} /> : <p className="text-[12px] text-muted-foreground">无 .ioc。查看 <Link href="/mcu/pins" className="underline">Pin Configuration</Link></p>}
        </div>
      )}
      {tab === "Clock" && <ClockTree clock={ioc?.clock} />}
      {tab === "Memory" && (
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-md border border-border bg-panel p-3">
            <div className="text-[11px] text-muted-foreground">Flash</div>
            <div className="font-mono text-[18px]">{mcu.flashKb} KB</div>
          </div>
          <div className="rounded-md border border-border bg-panel p-3">
            <div className="text-[11px] text-muted-foreground">RAM</div>
            <div className="font-mono text-[18px]">{mcu.ramKb} KB</div>
          </div>
        </div>
      )}
      {tab === "Peripherals" && (
        <div className="grid grid-cols-4 gap-2 md:grid-cols-8">
          {mcu.peripherals.map((p) => (
            <div key={p.name} className="rounded-md border border-border bg-panel p-2 text-center">
              <div className="font-mono text-[16px]">{p.count}</div>
              <div className="text-[11px] text-muted-foreground">{p.name}</div>
            </div>
          ))}
        </div>
      )}
      {tab === "Interrupts" && (
        <div className="font-mono text-[12px] text-muted-foreground">{ioc?.nvic.join(" · ") || "无 IOC NVIC 数据"}</div>
      )}
      {tab === "Alternate Functions" && (
        <div className="font-mono text-[12px] text-muted-foreground">
          {ioc?.pins.filter((p) => p.signal.includes("_")).map((p) => `${p.pin}=${p.signal}`).join(" · ") || "无 AF 数据"}
        </div>
      )}
      {tab === "Board" && (
        <dl className="space-y-1 text-[12px]">
          <div className="flex justify-between"><dt className="text-muted-foreground">Board</dt><dd className="font-mono">{ctx.board}</dd></div>
          <div className="flex justify-between"><dt className="text-muted-foreground">Debugger</dt><dd className="font-mono">{ctx.debugger}</dd></div>
          <div className="flex justify-between"><dt className="text-muted-foreground">HSE</dt><dd className="font-mono">{ctx.hse ?? "—"}</dd></div>
        </dl>
      )}
    </div>
  );
}

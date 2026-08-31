"use client";

import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { usePathname } from "next/navigation";
import { PlanViewer } from "@/components/agent/PlanViewer";
import { useWorkspace } from "@/lib/stores/workspace";
import { MCUInfo } from "@/components/mcu/MCUInfo";
import { currentMcu } from "@/lib/mock/mcu";
import { SerialMonitor } from "@/components/terminal/SerialMonitor";

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const plan = useWorkspace((s) => s.plan);
  const serialLines = useWorkspace((s) => s.serialLines);
  const diffs = useWorkspace((s) => s.diffs);
  const acceptAll = useWorkspace((s) => s.acceptAll);

  let context: ReactNode = <PlanViewer plan={plan} />;
  if (pathname.startsWith("/serial")) {
    context = (
      <div className="flex h-full flex-col">
        <div className="border-b border-border px-3 py-2 text-[11px] font-medium text-muted-foreground">
          AI Analysis
        </div>
        <div className="space-y-2 p-3 text-[12px]">
          <p>串口输出正常。</p>
          <p>
            LED 周期：<span className="font-mono">1000ms</span>
          </p>
          <p className="text-success">符合预期：✓</p>
        </div>
        <div className="min-h-0 flex-1 border-t border-border">
          <SerialMonitor lines={serialLines} />
        </div>
      </div>
    );
  } else if (pathname.startsWith("/code")) {
    context = (
      <div className="p-3 text-[12px]">
        <div className="text-[11px] text-muted-foreground">AI 修改</div>
        <p className="mt-2">
          {diffs.length ? `${diffs.length} 个文件有待处理 Diff` : "当前没有待处理的 AI Diff。"}
        </p>
        {diffs.some((d) => d.accepted == null) && (
          <button onClick={acceptAll} className="mt-3 rounded-sm bg-primary px-2 py-1 text-primary-foreground">
            Accept All
          </button>
        )}
      </div>
    );
  } else if (pathname.startsWith("/mcu")) {
    context = (
      <div className="overflow-auto p-3">
        <MCUInfo mcu={currentMcu} />
      </div>
    );
  } else if (pathname === "/" || pathname.startsWith("/projects") || pathname.startsWith("/settings")) {
    context = null;
  }

  return <AppShell context={context}>{children}</AppShell>;
}

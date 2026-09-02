"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";
import { StatusBadge } from "@/components/common/StatusBadge";
import { HardwareRunButton } from "@/components/hardware/HardwareRunButton";
import { HardwareTimeline } from "@/components/hardware/HardwareTimeline";
import { ValidationTimeline } from "@/components/hardware/ValidationTimeline";
import { SerialMonitor } from "@/components/hardware/SerialMonitor";
import { ValidationReport } from "@/components/validation/ValidationReport";
import { useHardware } from "@/lib/stores/hardware-store";
import { useAgent } from "@/lib/stores/agent-store";
import { useLive } from "@/lib/stores/live-store";
import { useProject } from "@/lib/stores/project-store";
import { useTerminal } from "@/lib/stores/terminal-store";
import { runAutoDebug } from "@/lib/api/validation";
import type { CapabilityStatus } from "@/types/status";

const RESULT_ROWS: Array<{ id: string; label: string; kinds: string[] }> = [
  { id: "mcu", label: "MCU", kinds: ["detect"] },
  { id: "flash", label: "Flash", kinds: ["flash"] },
  { id: "sram", label: "SRAM", kinds: [] },
  { id: "clock", label: "Clock", kinds: [] },
  { id: "swd", label: "SWD", kinds: ["detect"] },
  { id: "uart", label: "UART", kinds: ["serial", "validate"] },
  { id: "gpio", label: "GPIO", kinds: ["validate"] },
  { id: "button", label: "Button", kinds: [] },
  { id: "led", label: "LED", kinds: ["validate"] },
];

function rowStatus(run: { available: boolean; steps: Array<{ kind: string; status: string }> } | undefined, kinds: string[]): CapabilityStatus {
  if (!run) return "not_tested";
  if (!run.available) return "unavailable";
  if (!kinds.length) return "unavailable";
  const steps = run.steps.filter((s) => kinds.includes(s.kind));
  if (!steps.length) return "not_tested";
  if (steps.some((s) => s.status === "failed")) return "fail";
  if (steps.some((s) => s.status === "unavailable")) return "unavailable";
  if (steps.every((s) => s.status === "success")) return "pass";
  return "unknown";
}

export default function DebugCenterPage() {
  const mode = useLive((s) => s.mode);
  const run = useHardware((s) => s.hardwareRun);
  const setRun = useHardware((s) => s.setHardwareRun);
  const ctx = useHardware((s) => s.context);
  const validations = useAgent((s) => s.validations);
  const projectId = useProject((s) => s.projectId);
  const terminalLines = useTerminal((s) => s.terminalLines);
  const [msg, setMsg] = useState("");
  const last = validations.at(-1);

  const diagnosis = useMemo(() => {
    const notes: string[] = [];
    if (!run) return notes;
    if (!run.available) {
      notes.push(run.reason || "Hardware pipeline unavailable");
      return notes;
    }
    const serial = run.steps.find((s) => s.kind === "serial");
    const flash = run.steps.find((s) => s.kind === "flash");
    if (flash?.status === "success" && (serial?.status === "failed" || serial?.status === "unavailable")) {
      notes.push("串口无数据");
    }
    if (run.validation && /115200|104167|baud|clock/i.test(`${run.validation.expected} ${run.validation.actual}`)) {
      notes.push("时钟偏差 / 波特率不匹配");
    }
    if (run.validation?.status === "fail") notes.push("功能验证未通过");
    return notes;
  }, [run]);

  return (
    <div className="h-full overflow-auto p-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-semibold">Debug & Hardware Validation</h1>
          <p className="text-[12px] text-muted-foreground">无证据不写 PASS。GDB 寄存器当前 Not Available。</p>
        </div>
        <HardwareRunButton />
      </div>

      <div className="grid gap-3 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)_minmax(260px,0.7fr)]">
        <section className="rounded-md border border-border bg-panel p-3">
          <h2 className="text-[12px] font-medium">Debug Session</h2>
          <dl className="mt-2 space-y-1 text-[12px]">
            <div className="flex justify-between"><dt className="text-muted-foreground">状态</dt><dd>Not Connected</dd></div>
            <div className="flex justify-between"><dt className="text-muted-foreground">MCU</dt><dd className="font-mono">{ctx.mcu}</dd></div>
            <div className="flex justify-between"><dt className="text-muted-foreground">Clock</dt><dd className="font-mono">{ctx.clock || "unknown"}</dd></div>
            <div className="flex justify-between"><dt className="text-muted-foreground">Connection</dt><dd>Not Available</dd></div>
            <div className="flex justify-between"><dt className="text-muted-foreground">Reset reason</dt><dd>UNKNOWN</dd></div>
          </dl>
          <div className="mt-3">
            <CapabilityBanner reason="Backend Not Implemented — 无 GDB/OpenOCD 寄存器 API。Breakpoints / Call Stack / Watch / Registers 为 Experimental。" />
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-[12px]">
            <div className="rounded-sm border border-border p-2">
              <div className="text-[11px] text-muted-foreground">Breakpoints</div>
              <div>Not Available</div>
            </div>
            <div className="rounded-sm border border-border p-2">
              <div className="text-[11px] text-muted-foreground">Call Stack</div>
              <div>Not Available</div>
            </div>
            <div className="rounded-sm border border-border p-2">
              <div className="text-[11px] text-muted-foreground">Watch</div>
              <div>Not Available</div>
            </div>
            <div className="rounded-sm border border-border p-2">
              <div className="text-[11px] text-muted-foreground">Registers</div>
              <div>Not Available</div>
            </div>
          </div>
        </section>

        <section className="rounded-md border border-border bg-panel p-3">
          <h2 className="text-[12px] font-medium">Hardware Validation Timeline</h2>
          <div className="mt-2">
            <ValidationTimeline result={run} />
          </div>
          <h3 className="mt-4 text-[12px] font-medium">Pipeline</h3>
          <HardwareTimeline result={run} />
        </section>

        <section className="space-y-3">
          <div className="rounded-md border border-border bg-panel p-3">
            <h2 className="text-[12px] font-medium">Hardware Result</h2>
            <ul className="mt-2 space-y-1 text-[12px]">
              {RESULT_ROWS.map((r) => (
                <li key={r.id} className="flex items-center justify-between">
                  <span>{r.label}</span>
                  <StatusBadge status={rowStatus(run, r.kinds)} />
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-md border border-border bg-panel p-3">
            <h2 className="text-[12px] font-medium">Auto Diagnosis</h2>
            {diagnosis.length === 0 ? (
              <p className="mt-2 text-[12px] text-muted-foreground">尚无硬件证据，不会猜测成功。</p>
            ) : (
              <ul className="mt-2 list-disc pl-4 text-[12px] text-muted-foreground">
                {diagnosis.map((d) => (
                  <li key={d}>{d}</li>
                ))}
              </ul>
            )}
            <Button
              size="sm"
              className="mt-2"
              variant="outline"
              onClick={() => {
                void runAutoDebug(projectId).then((r) => {
                  if (!r.available) setMsg(r.reason ?? "Backend Not Implemented");
                  else setRun(r);
                });
              }}
            >
              Run Auto Debug
            </Button>
            {msg && <div className="mt-1 text-[11px] text-warning">{msg}</div>}
          </div>
        </section>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <section className="h-72 overflow-hidden rounded-md border border-border">
          <div className="border-b border-border px-3 py-1.5 text-[12px] font-medium">Serial Monitor</div>
          <SerialMonitor />
        </section>
        <section className="h-72 overflow-auto rounded-md border border-border bg-panel p-3">
          <h2 className="text-[12px] font-medium">Flash Log</h2>
          <pre className="mt-2 whitespace-pre-wrap font-mono text-[11px] text-muted-foreground">
            {terminalLines.slice(-30).join("\n") || (mode === "live" ? "尚无 flash 日志" : "DEMO / 离线无真实 Flash Log")}
          </pre>
        </section>
      </div>

      {run?.validation && (
        <div className="mt-3">
          <ValidationReport
            result={{
              id: run.runId ?? "hw",
              runId: run.runId ?? "hw",
              requirement: "Hardware pipeline",
              method: "Build / Flash / Serial",
              expected: run.validation.expected,
              observed: run.validation.actual,
              status: run.validation.status,
              confidence: run.validation.confidence,
            }}
          />
        </div>
      )}
      {last && !run?.validation && (
        <div className="mt-3">
          <ValidationReport result={last} />
        </div>
      )}
    </div>
  );
}

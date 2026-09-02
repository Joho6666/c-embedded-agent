"use client";

import { StatusBadge } from "@/components/common/StatusBadge";
import type { HardwarePipelineResult } from "@/types/hardware-run";
import type { CapabilityStatus } from "@/types/status";

const STAGES: Array<{ id: string; title: string; kinds: string[] }> = [
  { id: "detect", title: "Detect Probe", kinds: ["detect"] },
  { id: "identify", title: "Identify MCU", kinds: ["detect"] },
  { id: "reset", title: "Reset", kinds: ["reset"] },
  { id: "memory", title: "Memory Check", kinds: [] },
  { id: "register", title: "Register Check", kinds: [] },
  { id: "init", title: "Peripheral Init", kinds: [] },
  { id: "flash", title: "Flash", kinds: ["flash"] },
  { id: "runtime", title: "Runtime Validation", kinds: ["serial"] },
  { id: "functional", title: "Functional Validation", kinds: ["validate"] },
];

function mapStatus(result?: HardwarePipelineResult, kinds?: string[]): CapabilityStatus {
  if (!result) return "not_tested";
  if (!result.available) return "unavailable";
  if (!kinds?.length) return "unavailable";
  const steps = result.steps.filter((s) => kinds.includes(s.kind));
  if (!steps.length) return "not_tested";
  if (steps.some((s) => s.status === "failed")) return "fail";
  if (steps.some((s) => s.status === "unavailable")) return "unavailable";
  if (steps.every((s) => s.status === "success")) return "pass";
  if (steps.some((s) => s.status === "running")) return "unknown";
  return "unknown";
}

export function ValidationTimeline({ result }: { result?: HardwarePipelineResult }) {
  return (
    <ol className="space-y-1">
      {STAGES.map((s) => {
        const status = mapStatus(result, s.kinds);
        return (
          <li key={s.id} className="flex items-center justify-between rounded-sm border border-border px-2 py-1.5 text-[12px]">
            <span>{s.title}</span>
            <StatusBadge status={status} />
          </li>
        );
      })}
    </ol>
  );
}

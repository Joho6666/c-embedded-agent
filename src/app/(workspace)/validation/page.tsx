"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ValidationReport } from "@/components/validation/ValidationReport";
import { HardwareTimeline } from "@/components/hardware/HardwareTimeline";
import { HardwareRunButton } from "@/components/hardware/HardwareRunButton";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";
import { useHardware } from "@/lib/stores/hardware-store";
import { useAgent } from "@/lib/stores/agent-store";
import { runAutoDebug } from "@/lib/api/validation";
import { useProject } from "@/lib/stores/project-store";
import { useState } from "react";

const RULES = [
  "SerialContains",
  "SerialFrequency",
  "BuildSuccess",
  "NoCompilerError",
  "NoCppcheckError",
  "MCUMatch",
  "FlashVerified",
];

export default function ValidationPage() {
  const run = useHardware((s) => s.hardwareRun);
  const setRun = useHardware((s) => s.setHardwareRun);
  const validations = useAgent((s) => s.validations);
  const projectId = useProject((s) => s.projectId);
  const setPrompt = useAgent((s) => s.setPrompt);
  const router = useRouter();
  const [debugMsg, setDebugMsg] = useState("");

  const last = validations.at(-1);
  const serialFailed = run?.steps.some((s) => s.kind === "flash" && s.status === "success") && run.steps.some((s) => s.kind === "serial" && (s.status === "failed" || s.status === "unavailable"));

  return (
    <div className="p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-semibold">Hardware Validation</h1>
          <p className="text-[12px] text-muted-foreground">Expected / Actual / Result。无硬件证据时显示 unknown，不伪装 PASSED。</p>
        </div>
        <HardwareRunButton />
      </div>
      <div className="mb-4 flex flex-wrap gap-1 text-[11px] text-muted-foreground">
        {RULES.map((r) => (
          <span key={r} className="rounded-sm border border-border px-1.5 py-0.5 font-mono">
            {r}
          </span>
        ))}
      </div>
      {!run && !last ? <CapabilityBanner reason="Not Tested" kind="not-tested" /> : null}
      {run && !run.available ? <CapabilityBanner reason={run.reason} /> : null}
      {run?.validation && (
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
      )}
      {last && !run?.validation && <div className="mt-4"><ValidationReport result={last} /></div>}
      <h2 className="mt-6 text-[13px] font-medium">Hardware Timeline</h2>
      <div className="mt-2">
        <HardwareTimeline result={run} />
      </div>
      {serialFailed && (
        <div className="mt-4 rounded-md border border-error/40 bg-error/10 p-3 text-[12px]">
          <div className="font-medium">Hardware Validation Failed</div>
          <div className="mt-1 text-muted-foreground">Possible Causes:</div>
          <ul className="mt-1 list-disc pl-4 text-muted-foreground">
            <li>USART 未初始化</li>
            <li>GPIO AF 错误</li>
            <li>Baud Rate 不匹配</li>
            <li>Clock 配置错误</li>
          </ul>
          <Button
            size="sm"
            className="mt-2"
            onClick={() => {
              void runAutoDebug(projectId).then((r) => {
                if (!r.available) setDebugMsg(r.reason ?? "Backend Not Implemented");
                else setRun(r);
              });
            }}
          >
            Run Auto Debug
          </Button>
          {debugMsg && <div className="mt-2 text-[11px]">{debugMsg}</div>}
          <Button
            size="sm"
            variant="outline"
            className="mt-2 ml-1"
            onClick={() => {
              setPrompt("Flash 成功但串口无输出。请检查 USART 初始化、GPIO AF、波特率和时钟。");
              router.push("/agent");
            }}
          >
            Ask Agent
          </Button>
        </div>
      )}
    </div>
  );
}

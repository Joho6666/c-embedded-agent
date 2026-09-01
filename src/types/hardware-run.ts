export type HardwareRunStepKind =
  | "build"
  | "detect"
  | "flash"
  | "reset"
  | "serial"
  | "validate"
  | "autodebug"
  | "memory_match";

export type HardwareStepStatus = "pending" | "running" | "success" | "failed" | "unavailable";

export interface HardwareRunStep {
  id: string;
  kind: HardwareRunStepKind;
  title: string;
  status: HardwareStepStatus;
  detail?: string;
  logs?: string;
  reason?: string;
}

export interface HardwarePipelineResult {
  available: boolean;
  reason?: string;
  runId?: string;
  steps: HardwareRunStep[];
  validation?: {
    expected: string;
    actual: string;
    status: "pass" | "fail" | "unknown";
    confidence: number | null;
  };
}

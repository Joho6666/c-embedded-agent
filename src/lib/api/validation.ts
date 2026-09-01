import { apiFetch } from "./client";
import type { HardwarePipelineResult } from "@/types/hardware-run";
import type { ValidationResult } from "@/types/validation";

export async function runHardwarePipeline(input: {
  projectId: string;
  serialDevice?: string;
  baud?: number;
  expect?: string;
}): Promise<HardwarePipelineResult> {
  try {
    return await apiFetch<HardwarePipelineResult>("/api/hardware/run", {
      method: "POST",
      body: JSON.stringify(input),
    });
  } catch (e) {
    return {
      available: false,
      reason: e instanceof Error && /404/.test(e.message) ? "Backend Not Implemented" : "Backend capability unavailable",
      steps: [],
    };
  }
}

export async function runAutoDebug(projectId: string): Promise<HardwarePipelineResult> {
  try {
    return await apiFetch<HardwarePipelineResult>("/api/hardware/auto-debug", {
      method: "POST",
      body: JSON.stringify({ projectId }),
    });
  } catch {
    return {
      available: false,
      reason: "Backend Not Implemented",
      steps: [],
    };
  }
}

export async function getValidation(runId?: string): Promise<{ available: boolean; reason?: string; result?: ValidationResult }> {
  try {
    const path = runId ? `/api/validation?runId=${encodeURIComponent(runId)}` : "/api/validation";
    const result = await apiFetch<ValidationResult>(path);
    return { available: true, result };
  } catch (e) {
    return {
      available: false,
      reason: e instanceof Error && /404/.test(e.message) ? "Backend Not Implemented" : "Backend capability unavailable",
    };
  }
}

import { apiFetch } from "./client";
import type { BenchmarkSummary } from "@/types/benchmark";

export async function getBenchmarkDashboard(): Promise<BenchmarkSummary> {
  try {
    const raw = await apiFetch<Record<string, unknown>>("/api/benchmark");
    if (raw && typeof raw.available === "boolean") {
      return raw as unknown as BenchmarkSummary;
    }
    return wrapMetrics(raw);
  } catch {
    try {
      const raw = await apiFetch<Record<string, unknown>>("/api/metrics");
      return wrapMetrics(raw);
    } catch (e) {
      return {
        available: false,
        reason: e instanceof Error && /404/.test(e.message) ? "Backend Not Implemented" : "Backend capability unavailable",
        bySkill: [],
        models: [],
      };
    }
  }
}

function wrapMetrics(raw: Record<string, unknown>): BenchmarkSummary {
  const skipped = Array.isArray(raw.skipped) ? (raw.skipped as string[]) : [];
  const compile = typeof raw.compile_success_rate === "number" ? raw.compile_success_rate : null;
  const first = typeof raw.first_build_success_rate === "number" ? raw.first_build_success_rate : null;
  const auto = typeof raw.auto_fix_success_rate === "number" ? raw.auto_fix_success_rate : null;
  const avg = typeof raw.avg_iterations === "number" ? raw.avg_iterations : null;
  const hasRates = compile != null || first != null;
  return {
    available: true,
    reason: hasRates ? undefined : skipped.length ? skipped.join(" · ") : "No benchmark data",
    mcu: "STM32F103",
    tasks: typeof raw.tasks === "number" ? raw.tasks : typeof raw.n === "number" ? (raw.n as number) : null,
    compileSuccess: compile,
    firstBuildSuccess: first,
    autoFix: auto,
    avgIterations: avg,
    skipped,
    bySkill: [],
    models: [],
    gcc: typeof raw.gcc === "boolean" ? raw.gcc : undefined,
    llm: typeof raw.llm === "boolean" ? raw.llm : undefined,
  };
}

export interface BuildResult {
  number: number;
  status: "success" | "failed" | "running";
  durationSec: number;
  flashUsedKb: number;
  flashTotalKb: number;
  ramUsedKb: number;
  ramTotalKb: number;
  warnings: number;
  errors: number;
  output: string[];
}

export interface Problem {
  id: string;
  file: string;
  line: number;
  severity: "error" | "warning";
  message: string;
  suggestion?: string;
  source?: "gcc" | "clangd" | "cppcheck" | "ceedling" | "agent";
}

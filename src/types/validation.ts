export type ValidationStatus = "pass" | "fail" | "unknown";

export interface ValidationResult {
  id: string;
  runId: string;
  requirement: string;
  method: string;
  expected: string;
  observed: string;
  tolerance?: string;
  status: ValidationStatus;
  evidence?: string;
}

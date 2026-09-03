export type ValidationStatus = "pass" | "fail" | "unknown";

export type ValidationRuleKind =
  | "SerialContains"
  | "SerialFrequency"
  | "BuildSuccess"
  | "NoCompilerError"
  | "NoCppcheckError"
  | "MCUMatch"
  | "FlashVerified"
  | "GPIOProbe"
  | "LogicAnalyzer"
  | "CurrentMeasurement"
  | "Oscilloscope";

export interface ValidationRule {
  id: string;
  kind: ValidationRuleKind;
  label: string;
  expected?: string;
  implemented: boolean;
}

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
  confidence?: number | null;
  rules?: ValidationRule[];
}

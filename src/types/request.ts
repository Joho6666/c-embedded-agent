export type RequestStatusCode =
  | 200
  | 400
  | 401
  | 403
  | 429
  | 500
  | 502
  | "timeout"
  | "quota_exhausted"
  | "circuit_open"
  | "disabled";

export interface TraceEvent {
  at: string;
  label: string;
  detail?: string;
  kind?: "info" | "ok" | "warn" | "error";
}

export interface RequestLog {
  id: string;
  callId: string;
  time: string;
  clientKeyId: string;
  virtualModel: string;
  realModel: string;
  providerId: string;
  credentialId: string;
  status: RequestStatusCode;
  inputTokens: number;
  outputTokens: number;
  cachedTokens: number;
  ttftMs: number;
  latencyMs: number;
  retries: number;
  fallbackCount: number;
  cost: number;
  stream: boolean;
  error?: string;
  trace: TraceEvent[];
}

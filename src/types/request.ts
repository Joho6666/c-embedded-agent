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
  | "disabled"
  | "pending"
  | "routing"
  | "connecting"
  | "streaming"
  | "ok"
  | "error"
  | "cancelled";

export interface TraceEvent {
  at: string;
  timestamp?: string;
  durationMs?: number;
  type?: string;
  provider?: string;
  credential?: string;
  model?: string;
  message?: string;
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
  requestStatus?: string;
  startedAt?: string | null;
  firstTokenAt?: string | null;
  completedAt?: string | null;
  streamCompleted?: boolean;
  clientDisconnected?: boolean;
  inputTokens: number;
  outputTokens: number;
  cachedTokens: number;
  reasoningTokens?: number;
  ttftMs: number;
  latencyMs: number;
  retries: number;
  fallbackCount: number;
  cost: number;
  stream: boolean;
  error?: string;
  trace: TraceEvent[];
}

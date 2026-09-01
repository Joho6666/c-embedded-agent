export type LogStatus = "success" | "error" | "timeout";

export interface RequestLog {
  id: string;
  time: string;
  requestId: string;
  user: string;
  keyId: string;
  keyName: string;
  model: string;
  providerId: string;
  promptTokens: number;
  completionTokens: number;
  cost: number;
  latency: number;
  status: LogStatus;
  errorMessage?: string;
  endpoint: string;
  stream: boolean;
}

export interface LogQuery {
  q?: string;
  model?: string;
  providerId?: string;
  keyId?: string;
  status?: LogStatus | "all";
  from?: string;
  to?: string;
  page?: number;
  pageSize?: number;
}

export interface Paged<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export type ProviderTemplate =
  | "openai"
  | "anthropic"
  | "gemini"
  | "openrouter"
  | "newapi"
  | "oneapi"
  | "custom";

export type HealthStatus = "healthy" | "degraded" | "error" | "disabled";

export interface Provider {
  id: string;
  name: string;
  type: ProviderTemplate;
  baseUrl: string;
  balance: number;
  modelCount: number;
  todayCalls: number;
  successRate: number;
  avgLatency: number;
  priority: number;
  weight: number;
  health: HealthStatus;
  enabled: boolean;
  createdAt: string;
}

export interface ProviderInput {
  name: string;
  type: ProviderTemplate;
  baseUrl: string;
  priority: number;
  weight: number;
}

export interface ProviderTestResult {
  ok: boolean;
  latency: number;
  message: string;
}

export interface BalanceResult {
  balance: number;
  currency: string;
}

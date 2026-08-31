import type { CredentialStatus } from "./credential";
import type { ProviderStatus } from "./provider";

export type ComponentHealth = "operational" | "degraded" | "down";

export interface HealthComponent {
  id: string;
  name: string;
  status: ComponentHealth;
  latencyMs?: number;
  detail: string;
}

export interface ProviderHealth {
  providerId: string;
  status: ProviderStatus;
  latencyMs: number;
  successRate: number;
}

export interface CredentialHealthCount {
  status: CredentialStatus;
  count: number;
}

export interface CircuitBreaker {
  id: string;
  credentialId: string;
  providerId: string;
  reason: string;
  lastError: string;
  failureCount: number;
  openedAt: string;
  recoverAt: string;
  cooldownRemainingSec: number;
}

export interface HealthSnapshot {
  overall: ComponentHealth;
  checkedAt: string;
  components: HealthComponent[];
  providers: ProviderHealth[];
  credentialCounts: CredentialHealthCount[];
}

export interface OverviewMetrics {
  requestsToday: number;
  tokensToday: number;
  estimatedCost: number;
  successRate: number;
  avgTtftMs: number;
  avgLatencyMs: number;
  activeProviders: number;
  healthyCredentials: number;
  circuitOpen: number;
  availableModels: number;
  rpm: number;
  activeClients: number;
}

export interface TrafficShare {
  providerId: string;
  name: string;
  pct: number;
  color: string;
}

export interface UsagePoint {
  t: string;
  requests: number;
  tokens: number;
  cost: number;
  errors: number;
  latency: number;
}

export type UsageRange = "today" | "24h" | "7d" | "30d";

export interface UsageSlice {
  range: UsageRange;
  totals: {
    requests: number;
    tokens: number;
    inputTokens: number;
    outputTokens: number;
    cachedTokens: number;
    cost: number;
    successRate: number;
    errorRate: number;
    latency: number;
    ttft: number;
  };
  trend: UsagePoint[];
  byProvider: { id: string; name: string; value: number; color: string }[];
  byModel: { id: string; name: string; value: number }[];
  byCredential: { id: string; name: string; value: number }[];
  byKey: { id: string; name: string; value: number }[];
  errors: { name: string; value: number }[];
}

export interface GatewaySettings {
  gatewayUrl: string;
  timeoutMs: number;
  retries: number;
  logRetentionDays: number;
  oauthCredentials: boolean;
  usdBudget: boolean;
  theme: "dark" | "light" | "system";
}

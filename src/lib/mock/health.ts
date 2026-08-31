import type { CircuitBreaker, GatewaySettings, HealthSnapshot } from "@/types";
import { credentials } from "./credentials";
import { providers } from "./providers";

export const healthSnapshot: HealthSnapshot = {
  overall: "operational",
  checkedAt: new Date().toISOString(),
  components: [
    { id: "gateway", name: "Gateway", status: "operational", latencyMs: 4, detail: "http://localhost:8000/v1" },
    { id: "database", name: "Database", status: "operational", latencyMs: 6, detail: "Postgres primary" },
    { id: "redis", name: "Redis", status: "operational", latencyMs: 1, detail: "routing cache" },
    { id: "providers", name: "Providers", status: "degraded", detail: "Claude degraded · Hunyuan error" },
    { id: "credentials", name: "Credentials", status: "degraded", detail: "3 circuit open · 1 cooling" },
    { id: "models", name: "Models", status: "operational", detail: "48 available" },
    { id: "worker", name: "Worker", status: "operational", latencyMs: 12, detail: "1 replica" },
  ],
  providers: providers.map((p) => ({
    providerId: p.id,
    status: p.status,
    latencyMs: p.latencyMs,
    successRate: p.successRate,
  })),
  credentialCounts: [
    { status: "healthy", count: credentials.filter((c) => c.status === "healthy").length },
    { status: "rate_limited", count: credentials.filter((c) => c.status === "rate_limited").length },
    { status: "cooling", count: credentials.filter((c) => c.status === "cooling").length },
    { status: "circuit_open", count: credentials.filter((c) => c.status === "circuit_open").length },
    { status: "unauthorized", count: credentials.filter((c) => c.status === "unauthorized").length },
    { status: "quota_exhausted", count: credentials.filter((c) => c.status === "quota_exhausted").length },
    { status: "disabled", count: credentials.filter((c) => c.status === "disabled").length },
    { status: "error", count: credentials.filter((c) => c.status === "error").length },
  ],
};

export const circuitBreakers: CircuitBreaker[] = credentials
  .filter((c) => c.status === "circuit_open")
  .map((c, i) => ({
    id: `cb_${c.id}`,
    credentialId: c.id,
    providerId: c.providerId,
    reason: i === 0 ? "连续失败" : i === 1 ? "HTTP 5xx" : "连接失败",
    lastError: c.lastError ?? "unknown",
    failureCount: 5 + i * 2,
    openedAt: new Date(Date.now() - (22 + i * 18) * 60_000).toISOString(),
    recoverAt: new Date(Date.now() + (8 + i * 4) * 60_000).toISOString(),
    cooldownRemainingSec: (8 + i * 4) * 60,
  }));

export const defaultSettings: GatewaySettings = {
  gatewayUrl: "http://localhost:8000/v1",
  timeoutMs: 60_000,
  retries: 2,
  logRetentionDays: 14,
  oauthCredentials: true,
  usdBudget: true,
  theme: "dark",
};

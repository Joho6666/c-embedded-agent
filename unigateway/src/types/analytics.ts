import type { HealthStatus } from "./provider";
import type { RequestLog } from "./log";

export type TimeRange = "today" | "7d" | "30d" | "custom";

export interface TimePoint {
  t: string;
  requests: number;
  tokens: number;
  cost: number;
  latency: number;
  errors: number;
}

export interface RankItem {
  id: string;
  name: string;
  value: number;
  extra?: string;
}

export interface AnalyticsSnapshot {
  range: TimeRange;
  totals: {
    requests: number;
    tokens: number;
    cost: number;
    latency: number;
    errorRate: number;
  };
  series: TimePoint[];
  modelDistribution: { name: string; value: number }[];
  providerDistribution: { name: string; value: number }[];
  ranks: {
    expensiveModels: RankItem[];
    popularModels: RankItem[];
    slowestProviders: RankItem[];
    failingProviders: RankItem[];
    topKeys: RankItem[];
  };
}

export interface DashboardSnapshot {
  todayRequests: number;
  todayTokens: number;
  todayCost: number;
  successRate: number;
  avgLatency: number;
  activeKeys: number;
  onlineProviders: number;
  deltas: {
    requests: number;
    tokens: number;
    cost: number;
    successRate: number;
    latency: number;
  };
  series: TimePoint[];
  modelRank: RankItem[];
  providerHealth: {
    id: string;
    name: string;
    health: HealthStatus;
    successRate: number;
    latency: number;
  }[];
  recentLogs: RequestLog[];
  alerts: AlertItem[];
}

export interface AlertItem {
  id: string;
  severity: "warning" | "error";
  title: string;
  detail: string;
  time: string;
}

export interface MonitorEndpoint {
  providerId: string;
  name: string;
  endpoint: string;
  health: HealthStatus;
  successRate: number;
  p50: number;
  p95: number;
  p99: number;
  errorRate: number;
  uptime: number[];
}

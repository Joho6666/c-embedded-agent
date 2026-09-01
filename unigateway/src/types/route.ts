import type { HealthStatus } from "./provider";

export type RouteStrategy =
  | "cheapest"
  | "fastest"
  | "stable"
  | "weighted"
  | "random"
  | "failover"
  | "custom";

export interface RouteTarget {
  providerId: string;
  weight: number;
  priority: number;
  successRate: number;
  avgLatency: number;
  inputPrice: number;
  outputPrice: number;
  health: HealthStatus;
}

export interface RoutePolicy {
  id: string;
  modelAlias: string;
  displayName: string;
  strategy: RouteStrategy;
  targets: RouteTarget[];
}

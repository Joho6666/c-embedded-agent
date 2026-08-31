export type RoutingStrategy =
  | "priority"
  | "round_robin"
  | "weighted_round_robin"
  | "least_latency"
  | "least_load"
  | "lowest_cost"
  | "highest_success"
  | "quota_aware"
  | "health_aware"
  | "failover"
  | "random"
  | "hybrid";

export type RouteRuleAction =
  | "switch_credential"
  | "disable_credential"
  | "circuit_break"
  | "reduce_weight"
  | "lower_priority"
  | "failover_provider";

export interface RouteTarget {
  id: string;
  credentialId: string;
  modelId: string;
  weight: number;
  priority: number;
}

export interface RouteRule {
  id: string;
  when: string;
  action: RouteRuleAction;
  enabled: boolean;
}

export interface RoutingPolicy {
  id: string;
  virtualModelId: string;
  strategy: RoutingStrategy;
  targets: RouteTarget[];
  rules: RouteRule[];
}

export interface FallbackHop {
  providerId: string;
  credentialId: string;
  modelId: string;
  result: "success" | "fail";
  reason?: string;
}

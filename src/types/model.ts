import type { CapabilityKind } from "./provider";
import type { RoutingStrategy } from "./routing";

export type ModelStatus = "available" | "degraded" | "unavailable";

export interface RealModel {
  id: string;
  providerId: string;
  name: string;
  modelId: string;
  capabilities: CapabilityKind[];
  contextWindow: number;
  inputPrice: number;
  outputPrice: number;
  ttftMs: number;
  tokensPerSec: number;
  successRate: number;
  credentialCount: number;
  status: ModelStatus;
  tags: string[];
}

export interface VirtualCandidate {
  modelId: string;
  credentialId?: string;
  priority: number;
  weight: number;
}

export interface VirtualModel {
  id: string;
  slug: string;
  name: string;
  description: string;
  candidates: VirtualCandidate[];
  strategy: RoutingStrategy;
  fallbackChain: string[];
  requestsToday: number;
  successRate: number;
}

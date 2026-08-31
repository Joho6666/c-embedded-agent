import type { AuthScheme } from "./provider";

export type CredentialStatus =
  | "healthy"
  | "rate_limited"
  | "cooling"
  | "circuit_open"
  | "unauthorized"
  | "quota_exhausted"
  | "disabled"
  | "error";

export interface CredentialQuota {
  rpmLimit: number;
  rpmUsed: number;
  tpmLimit: number;
  tpmUsed: number;
  dailyRequestLimit: number;
  dailyRequestUsed: number;
  dailyTokenLimit: number;
  dailyTokenUsed: number;
  monthlyBudget: number;
  monthlySpend: number;
}

export interface CredentialError {
  at: string;
  code: string;
  message: string;
}

export interface Credential {
  id: string;
  providerId: string;
  name: string;
  authType: AuthScheme;
  status: CredentialStatus;
  priority: number;
  weight: number;
  maskedKey?: string;
  extra: Record<string, string>;
  requestsToday: number;
  tokensToday: number;
  avgLatencyMs: number;
  successRate: number;
  lastUsed?: string;
  lastError?: string;
  coolingUntil?: string;
  quota: CredentialQuota;
  errorHistory: CredentialError[];
  enabled: boolean;
}

export interface CredentialInput {
  providerId: string;
  name: string;
  authType: AuthScheme;
  extra: Record<string, string>;
  priority?: number;
  weight?: number;
}

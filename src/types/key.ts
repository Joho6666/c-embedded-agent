export type ApiKeyStatus = "active" | "disabled" | "expired";

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  secret: string;
  status: ApiKeyStatus;
  allowedVirtualModels: string[];
  rpmLimit: number;
  tpmLimit: number;
  dailyTokenLimit: number;
  monthlyBudget: number;
  ipWhitelist: string[];
  expiresAt?: string;
  lastUsed?: string;
  requestsToday: number;
  tokensToday: number;
  costToday: number;
}

export interface ApiKeyInput {
  name: string;
  allowedVirtualModels: string[];
  rpmLimit: number;
  tpmLimit: number;
  dailyTokenLimit: number;
  monthlyBudget: number;
  ipWhitelist: string[];
  expiresAt?: string;
}

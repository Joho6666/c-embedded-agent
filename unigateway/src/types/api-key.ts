export type ApiKeyStatus = "active" | "disabled" | "expired";

export interface ApiKey {
  id: string;
  name: string;
  maskedKey: string;
  owner: string;
  allowedModels: string[];
  used: number;
  budget: number;
  rpm: number;
  tpm: number;
  createdAt: string;
  expiresAt: string | null;
  status: ApiKeyStatus;
}

export interface ApiKeyInput {
  name: string;
  owner: string;
  allowedModels: string[];
  budget: number;
  rpm: number;
  tpm: number;
  expiresAt: string | null;
}

export interface CreatedApiKey extends ApiKey {
  fullKey: string;
}

import { adminFetch, GATEWAY_V1, playgroundKey } from "@/lib/api/http";
import type {
  ApiKey,
  ApiKeyInput,
  CircuitBreaker,
  Credential,
  CredentialInput,
  HealthSnapshot,
  OverviewMetrics,
  Provider,
  RealModel,
  RequestLog,
  VirtualModel,
} from "@/types";

export interface ModelPricing {
  id: string;
  provider: string;
  model: string;
  inputPer1M: number;
  outputPer1M: number;
  cachedInputPer1M: number;
  reasoningPer1M: number;
  currency: string;
  effectiveFrom: string;
}

export const gatewayApi = {
  listProviders: () => adminFetch<Provider[]>("/admin/providers"),
  createProvider: (input: { descriptorId: string; name?: string; baseUrl?: string }) =>
    adminFetch<Provider>("/admin/providers", { method: "POST", body: JSON.stringify(input) }),
  testProvider: (id: string) =>
    adminFetch<{ ok: boolean; latencyMs: number; message: string }>(`/admin/providers/${id}/test`, { method: "POST" }),
  syncModels: (id: string) =>
    adminFetch<{ synced: number }>(`/admin/providers/${id}/sync-models`, { method: "POST" }),

  listCredentials: () => adminFetch<Credential[]>("/admin/credentials"),
  addCredential: (input: CredentialInput) =>
    adminFetch<Credential>("/admin/credentials", { method: "POST", body: JSON.stringify(input) }),
  patchCredential: (id: string, patch: Record<string, unknown>) =>
    adminFetch<Credential>(`/admin/credentials/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  testCredential: (id: string) =>
    adminFetch<{ ok: boolean; message: string }>(`/admin/credentials/${id}/test`, { method: "POST" }),
  recoverCredential: (id: string) =>
    adminFetch<Credential>(`/admin/credentials/${id}/recover`, { method: "POST" }),
  startOAuth: (input: { family: string; baseUrl?: string; managementKey?: string; credentialId?: string }) =>
    adminFetch<{
      ok: boolean;
      bridgeOnline?: boolean;
      family?: string;
      label?: string;
      bridge?: string;
      loginUrl?: string;
      message?: string;
      hint?: string;
      command?: string;
    }>("/admin/oauth/start", { method: "POST", body: JSON.stringify(input) }),

  listModels: () => adminFetch<RealModel[]>("/admin/models"),
  listVirtual: () => adminFetch<VirtualModel[]>("/admin/virtual-models"),
  addVirtual: (input: Partial<VirtualModel> & { slug: string }) =>
    adminFetch<VirtualModel>("/admin/virtual-models", { method: "POST", body: JSON.stringify(input) }),
  patchVirtual: (id: string, patch: Record<string, unknown>) =>
    adminFetch<VirtualModel>(`/admin/virtual-models/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),

  listKeys: () => adminFetch<ApiKey[]>("/admin/api-keys"),
  addKey: (input: ApiKeyInput) =>
    adminFetch<ApiKey>("/admin/api-keys", { method: "POST", body: JSON.stringify(input) }),
  rotateKey: (id: string) => adminFetch<ApiKey>(`/admin/api-keys/${id}/rotate`, { method: "POST" }),
  toggleKey: (id: string) => adminFetch<ApiKey>(`/admin/api-keys/${id}/toggle`, { method: "POST" }),
  deleteKey: (id: string) => adminFetch<{ ok: boolean }>(`/admin/api-keys/${id}`, { method: "DELETE" }),

  listRequests: () => adminFetch<RequestLog[]>("/admin/requests"),
  usage: () => adminFetch<OverviewMetrics>("/admin/usage"),
  health: () => adminFetch<HealthSnapshot>("/admin/health"),
  circuits: () => adminFetch<CircuitBreaker[]>("/admin/circuit-breakers"),
  capabilities: () => adminFetch<{ strategies: string[]; adapters: Record<string, Record<string, boolean>> }>("/admin/capabilities"),
  providerCapabilities: (id: string) =>
    adminFetch<{ id: string; type: string; capabilities: Record<string, boolean> }>(`/admin/providers/${id}/capabilities`),
  usageTrend: (range = "today") => adminFetch<{ range: string; trend: { t: string; requests: number; tokens: number; cost: number }[] }>(`/admin/usage/trend?range=${range}`),
  usageProviders: (range = "today") => adminFetch<Record<string, unknown>[]>(`/admin/usage/providers?range=${range}`),
  usageModels: (range = "today") => adminFetch<Record<string, unknown>[]>(`/admin/usage/models?range=${range}`),
  usageCredentials: (range = "today") => adminFetch<Record<string, unknown>[]>(`/admin/usage/credentials?range=${range}`),
  usageApiKeys: (range = "today") => adminFetch<Record<string, unknown>[]>(`/admin/usage/api-keys?range=${range}`),
  usageErrors: (range = "today") => adminFetch<{ name: string; value: number }[]>(`/admin/usage/errors?range=${range}`),
  listPricing: () => adminFetch<ModelPricing[]>("/admin/model-pricing"),
  createPricing: (input: Partial<ModelPricing> & { model: string }) =>
    adminFetch<ModelPricing>("/admin/model-pricing", { method: "POST", body: JSON.stringify(input) }),
  patchPricing: (id: string, patch: Record<string, unknown>) =>
    adminFetch<ModelPricing>(`/admin/model-pricing/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  deletePricing: (id: string) => adminFetch<{ ok: boolean }>(`/admin/model-pricing/${id}`, { method: "DELETE" }),

  async chatCompletions(body: Record<string, unknown>, key?: string) {
    const token = key || playgroundKey();
    const res = await fetch(`${GATEWAY_V1}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    return res;
  },
};

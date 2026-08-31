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

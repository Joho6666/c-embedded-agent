"use client";

import { create } from "zustand";
import type {
  ApiKey,
  ApiKeyInput,
  CircuitBreaker,
  Credential,
  CredentialInput,
  GatewaySettings,
  HealthSnapshot,
  OverviewMetrics,
  Provider,
  RealModel,
  RequestLog,
  VirtualModel,
} from "@/types";
import { gatewayApi } from "@/lib/services/gateway";
import { GATEWAY_V1 } from "@/lib/api/http";

const emptyHealth: HealthSnapshot = {
  overall: "operational",
  checkedAt: new Date().toISOString(),
  components: [],
  providers: [],
  credentialCounts: [],
};

const emptyMetrics: OverviewMetrics = {
  requestsToday: 0,
  tokensToday: 0,
  estimatedCost: 0,
  successRate: 100,
  avgTtftMs: 0,
  avgLatencyMs: 0,
  activeProviders: 0,
  healthyCredentials: 0,
  circuitOpen: 0,
  availableModels: 0,
  rpm: 0,
  activeClients: 0,
};

interface GatewayState {
  providers: Provider[];
  credentials: Credential[];
  models: RealModel[];
  virtualModels: VirtualModel[];
  keys: ApiKey[];
  logs: RequestLog[];
  circuits: CircuitBreaker[];
  health: HealthSnapshot;
  metrics: OverviewMetrics;
  settings: GatewaySettings;
  strategies: string[];
  hydrated: boolean;
  error?: string;
  hydrate: () => Promise<void>;
  addProvider: (input: { descriptorId: string; name?: string; baseUrl?: string }) => Promise<Provider>;
  addCredential: (input: CredentialInput) => Promise<Credential>;
  updateCredential: (id: string, patch: Partial<Credential>) => Promise<void>;
  toggleCredential: (id: string) => Promise<void>;
  recoverCircuit: (id: string) => Promise<void>;
  addVirtualModel: (vm: Omit<VirtualModel, "id" | "requestsToday" | "successRate">) => Promise<VirtualModel>;
  updateVirtualModel: (id: string, patch: Partial<VirtualModel>) => Promise<void>;
  updateRoute: (virtualModelId: string, patch: { strategy?: VirtualModel["strategy"]; targets?: unknown }) => Promise<void>;
  addKey: (input: ApiKeyInput) => Promise<ApiKey>;
  rotateKey: (id: string) => Promise<ApiKey>;
  toggleKey: (id: string) => Promise<void>;
  deleteKey: (id: string) => Promise<void>;
  updateSettings: (patch: Partial<GatewaySettings>) => void;
  refreshHealth: () => Promise<void>;
  prependLog: (log: RequestLog) => void;
  reloadLogs: () => Promise<void>;
}

export const useGateway = create<GatewayState>((set, get) => ({
  providers: [],
  credentials: [],
  models: [],
  virtualModels: [],
  keys: [],
  logs: [],
  circuits: [],
  health: emptyHealth,
  metrics: emptyMetrics,
  strategies: [],
  settings: {
    gatewayUrl: GATEWAY_V1,
    timeoutMs: 60_000,
    retries: 2,
    logRetentionDays: 14,
    oauthCredentials: true,
    usdBudget: true,
    theme: "dark",
  },
  hydrated: false,
  hydrate: async () => {
    try {
      const [providers, credentials, models, virtualModels, keys, logs, health, metrics, circuits, caps] = await Promise.all([
        gatewayApi.listProviders(),
        gatewayApi.listCredentials(),
        gatewayApi.listModels(),
        gatewayApi.listVirtual(),
        gatewayApi.listKeys(),
        gatewayApi.listRequests(),
        gatewayApi.health(),
        gatewayApi.usage(),
        gatewayApi.circuits(),
        gatewayApi.capabilities().catch(() => ({ strategies: [] as string[], adapters: {} })),
      ]);
      set({
        providers,
        credentials,
        models,
        virtualModels,
        keys,
        logs,
        health,
        metrics,
        circuits,
        strategies: caps.strategies || [],
        hydrated: true,
        error: undefined,
      });
    } catch (e) {
      set({ hydrated: true, error: e instanceof Error ? e.message : "hydrate failed" });
    }
  },
  addProvider: async (input) => {
    const p = await gatewayApi.createProvider(input);
    set((s) => ({ providers: s.providers.some((x) => x.id === p.id) ? s.providers : [p, ...s.providers] }));
    return p;
  },
  addCredential: async (input) => {
    const c = await gatewayApi.addCredential(input);
    set((s) => ({
      credentials: [c, ...s.credentials],
      providers: s.providers.map((p) => (p.id === c.providerId ? { ...p, credentialCount: p.credentialCount + 1 } : p)),
    }));
    return c;
  },
  updateCredential: async (id, patch) => {
    const next = await gatewayApi.patchCredential(id, patch as Record<string, unknown>);
    set((s) => ({ credentials: s.credentials.map((c) => (c.id === id ? next : c)) }));
  },
  toggleCredential: async (id) => {
    const cur = get().credentials.find((c) => c.id === id);
    const next = await gatewayApi.patchCredential(id, { enabled: !cur?.enabled });
    set((s) => ({ credentials: s.credentials.map((c) => (c.id === id ? next : c)) }));
  },
  recoverCircuit: async (id) => {
    const credId = id.startsWith("cb_") ? id.slice(3) : get().circuits.find((c) => c.id === id)?.credentialId || id;
    const next = await gatewayApi.recoverCredential(credId);
    set((s) => ({
      credentials: s.credentials.map((c) => (c.id === next.id ? next : c)),
      circuits: s.circuits.filter((c) => c.credentialId !== next.id && c.id !== id),
    }));
  },
  addVirtualModel: async (vm) => {
    const created = await gatewayApi.addVirtual({
      slug: vm.slug,
      name: vm.name,
      description: vm.description,
      candidates: vm.candidates,
      strategy: vm.strategy,
      fallbackChain: vm.fallbackChain,
    });
    set((s) => ({ virtualModels: [created, ...s.virtualModels] }));
    return created;
  },
  updateVirtualModel: async (id, patch) => {
    const next = await gatewayApi.patchVirtual(id, patch as Record<string, unknown>);
    set((s) => ({ virtualModels: s.virtualModels.map((v) => (v.id === id ? next : v)) }));
  },
  updateRoute: async (virtualModelId, patch) => {
    const vm = get().virtualModels.find((v) => v.id === virtualModelId);
    if (!vm) return;
    const body: Record<string, unknown> = {};
    if (patch.strategy) body.strategy = patch.strategy;
    await gatewayApi.patchVirtual(virtualModelId, body);
    if (patch.strategy) {
      set((s) => ({
        virtualModels: s.virtualModels.map((v) => (v.id === virtualModelId ? { ...v, strategy: patch.strategy! } : v)),
      }));
    }
  },
  addKey: async (input) => {
    const key = await gatewayApi.addKey(input);
    set((s) => ({ keys: [key, ...s.keys] }));
    return key;
  },
  rotateKey: async (id) => {
    const key = await gatewayApi.rotateKey(id);
    set((s) => ({ keys: s.keys.map((k) => (k.id === id ? key : k)) }));
    return key;
  },
  toggleKey: async (id) => {
    const key = await gatewayApi.toggleKey(id);
    set((s) => ({ keys: s.keys.map((k) => (k.id === id ? key : k)) }));
  },
  deleteKey: async (id) => {
    await gatewayApi.deleteKey(id);
    set((s) => ({ keys: s.keys.filter((k) => k.id !== id) }));
  },
  updateSettings: (patch) => set((s) => ({ settings: { ...s.settings, ...patch } })),
  refreshHealth: async () => {
    const [health, metrics, circuits] = await Promise.all([gatewayApi.health(), gatewayApi.usage(), gatewayApi.circuits()]);
    set({ health, metrics, circuits });
  },
  prependLog: (log) => set((s) => ({ logs: [log, ...s.logs].slice(0, 400) })),
  reloadLogs: async () => {
    const [logs, metrics] = await Promise.all([gatewayApi.listRequests(), gatewayApi.usage()]);
    set({ logs, metrics });
  },
}));

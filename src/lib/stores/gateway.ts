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
  Provider,
  RealModel,
  RequestLog,
  RoutingPolicy,
  VirtualModel,
} from "@/types";
import {
  apiKeys as seedKeys,
  circuitBreakers as seedCircuits,
  credentials as seedCreds,
  defaultSettings,
  healthSnapshot as seedHealth,
  providers as seedProviders,
  realModels as seedModels,
  requestLogs as seedLogs,
  routingPolicies as seedRoutes,
  virtualModels as seedVirtual,
} from "@/lib/mock";
import { getDescriptor } from "@/descriptors/providers";
import { uid } from "@/lib/utils";

interface GatewayState {
  providers: Provider[];
  credentials: Credential[];
  models: RealModel[];
  virtualModels: VirtualModel[];
  routes: RoutingPolicy[];
  keys: ApiKey[];
  logs: RequestLog[];
  circuits: CircuitBreaker[];
  health: HealthSnapshot;
  settings: GatewaySettings;
  hydrated: boolean;
  addProvider: (input: {
    descriptorId: string;
    name?: string;
    baseUrl?: string;
    extra?: Record<string, string>;
  }) => Provider;
  addCredential: (input: CredentialInput) => Credential;
  updateCredential: (id: string, patch: Partial<Credential>) => void;
  toggleCredential: (id: string) => void;
  recoverCircuit: (id: string) => void;
  addVirtualModel: (vm: Omit<VirtualModel, "id" | "requestsToday" | "successRate">) => VirtualModel;
  updateVirtualModel: (id: string, patch: Partial<VirtualModel>) => void;
  updateRoute: (virtualModelId: string, patch: Partial<RoutingPolicy>) => void;
  addKey: (input: ApiKeyInput) => ApiKey;
  rotateKey: (id: string) => ApiKey;
  toggleKey: (id: string) => void;
  deleteKey: (id: string) => void;
  updateSettings: (patch: Partial<GatewaySettings>) => void;
  refreshHealth: () => void;
  prependLog: (log: RequestLog) => void;
}

function clone<T>(v: T): T {
  return structuredClone(v);
}

export const useGateway = create<GatewayState>((set, get) => ({
  providers: clone(seedProviders),
  credentials: clone(seedCreds),
  models: clone(seedModels),
  virtualModels: clone(seedVirtual),
  routes: clone(seedRoutes),
  keys: clone(seedKeys),
  logs: clone(seedLogs),
  circuits: clone(seedCircuits),
  health: clone(seedHealth),
  settings: clone(defaultSettings),
  hydrated: true,
  addProvider: (input) => {
    const d = getDescriptor(input.descriptorId);
    if (!d) throw new Error("unknown provider");
    const existing = get().providers.find((p) => p.descriptorId === input.descriptorId && !d.builtin);
    if (existing && d.builtin) return existing;
    const provider: Provider = {
      id: d.builtin ? d.id : uid("prov"),
      descriptorId: d.id,
      name: input.name || d.name,
      family: d.family,
      status: "operational",
      color: d.color,
      mark: d.mark,
      local: d.local,
      custom: !d.builtin,
      baseUrl: input.baseUrl || d.defaultBaseUrl,
      regions: d.regions,
      capabilities: d.capabilities,
      endpoints: d.endpoints,
      authSchemes: d.authSchemes,
      credentialCount: 0,
      modelCount: 0,
      requestsToday: 0,
      tokensToday: 0,
      costToday: 0,
      latencyMs: 0,
      successRate: 100,
    };
    set((s) => {
      if (s.providers.some((p) => p.id === provider.id)) return s;
      return { providers: [provider, ...s.providers] };
    });
    return provider;
  },
  addCredential: (input) => {
    const cred: Credential = {
      id: uid("cred"),
      providerId: input.providerId,
      name: input.name,
      authType: input.authType,
      status: "healthy",
      priority: input.priority ?? 3,
      weight: input.weight ?? 10,
      maskedKey: input.extra.apiKey ? `${input.extra.apiKey.slice(0, 6)}…${input.extra.apiKey.slice(-4)}` : undefined,
      extra: { ...input.extra, apiKey: undefined as unknown as string },
      requestsToday: 0,
      tokensToday: 0,
      avgLatencyMs: 0,
      successRate: 100,
      lastUsed: new Date().toISOString(),
      quota: {
        rpmLimit: 120,
        rpmUsed: 0,
        tpmLimit: 400_000,
        tpmUsed: 0,
        dailyRequestLimit: 10_000,
        dailyRequestUsed: 0,
        dailyTokenLimit: 20_000_000,
        dailyTokenUsed: 0,
        monthlyBudget: 20,
        monthlySpend: 0,
      },
      errorHistory: [],
      enabled: true,
    };
    delete cred.extra.apiKey;
    set((s) => ({
      credentials: [cred, ...s.credentials],
      providers: s.providers.map((p) =>
        p.id === input.providerId ? { ...p, credentialCount: p.credentialCount + 1 } : p,
      ),
    }));
    return cred;
  },
  updateCredential: (id, patch) =>
    set((s) => ({ credentials: s.credentials.map((c) => (c.id === id ? { ...c, ...patch } : c)) })),
  toggleCredential: (id) =>
    set((s) => ({
      credentials: s.credentials.map((c) =>
        c.id === id
          ? {
              ...c,
              enabled: !c.enabled,
              status: c.enabled ? "disabled" : "healthy",
            }
          : c,
      ),
    })),
  recoverCircuit: (id) =>
    set((s) => ({
      circuits: s.circuits.filter((c) => c.id !== id && c.credentialId !== id),
      credentials: s.credentials.map((c) =>
        c.id === id || s.circuits.some((cb) => cb.id === id && cb.credentialId === c.id)
          ? { ...c, status: "healthy", lastError: undefined }
          : c,
      ),
    })),
  addVirtualModel: (vm) => {
    const created: VirtualModel = {
      ...vm,
      id: uid("vm"),
      requestsToday: 0,
      successRate: 100,
    };
    const route: RoutingPolicy = {
      id: uid("rp"),
      virtualModelId: created.id,
      strategy: created.strategy,
      targets: created.candidates.map((c, i) => ({
        id: uid("t"),
        credentialId: c.credentialId ?? "",
        modelId: c.modelId,
        weight: c.weight,
        priority: c.priority || i + 1,
      })),
      rules: [
        { id: uid("r"), when: "HTTP 429", action: "switch_credential", enabled: true },
        { id: uid("r"), when: "HTTP 401", action: "disable_credential", enabled: true },
        { id: uid("r"), when: "连续 5 次失败", action: "circuit_break", enabled: true },
      ],
    };
    set((s) => ({
      virtualModels: [created, ...s.virtualModels],
      routes: [route, ...s.routes],
    }));
    return created;
  },
  updateVirtualModel: (id, patch) =>
    set((s) => ({
      virtualModels: s.virtualModels.map((v) => (v.id === id ? { ...v, ...patch } : v)),
    })),
  updateRoute: (virtualModelId, patch) =>
    set((s) => ({
      routes: s.routes.map((r) => (r.virtualModelId === virtualModelId ? { ...r, ...patch } : r)),
      virtualModels: patch.strategy
        ? s.virtualModels.map((v) => (v.id === virtualModelId ? { ...v, strategy: patch.strategy! } : v))
        : s.virtualModels,
    })),
  addKey: (input) => {
    const secret = `sk-gw-${uid("k").slice(-10)}`;
    const key: ApiKey = {
      id: uid("key"),
      name: input.name,
      prefix: secret.slice(0, 8),
      secret,
      status: "active",
      allowedVirtualModels: input.allowedVirtualModels,
      rpmLimit: input.rpmLimit,
      tpmLimit: input.tpmLimit,
      dailyTokenLimit: input.dailyTokenLimit,
      monthlyBudget: input.monthlyBudget,
      ipWhitelist: input.ipWhitelist,
      expiresAt: input.expiresAt,
      lastUsed: undefined,
      requestsToday: 0,
      tokensToday: 0,
      costToday: 0,
    };
    set((s) => ({ keys: [key, ...s.keys] }));
    return key;
  },
  rotateKey: (id) => {
    const secret = `sk-gw-${uid("k").slice(-10)}`;
    let next!: ApiKey;
    set((s) => ({
      keys: s.keys.map((k) => {
        if (k.id !== id) return k;
        next = { ...k, secret, prefix: secret.slice(0, 8) };
        return next;
      }),
    }));
    return next;
  },
  toggleKey: (id) =>
    set((s) => ({
      keys: s.keys.map((k) =>
        k.id === id ? { ...k, status: k.status === "active" ? "disabled" : "active" } : k,
      ),
    })),
  deleteKey: (id) => set((s) => ({ keys: s.keys.filter((k) => k.id !== id) })),
  updateSettings: (patch) => set((s) => ({ settings: { ...s.settings, ...patch } })),
  refreshHealth: () =>
    set((s) => ({
      health: {
        ...s.health,
        checkedAt: new Date().toISOString(),
        overall: s.circuits.length ? "degraded" : "operational",
      },
    })),
  prependLog: (log) => set((s) => ({ logs: [log, ...s.logs].slice(0, 400) })),
}));

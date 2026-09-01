"use client";

import type {
  AnalyticsQuery,
  AnalyticsSnapshot,
  ApiKey,
  ApiKeyInput,
  BalanceResult,
  CreatedApiKey,
  DashboardSnapshot,
  LogQuery,
  Model,
  ModelInput,
  MonitorEndpoint,
  Paged,
  Provider,
  ProviderInput,
  ProviderTestResult,
  RequestLog,
  RoutePatch,
  RoutePolicy,
  RouteStrategy,
  RouteTarget,
  SettingsState,
  TimePoint,
  TimeRange,
  User,
  UserInput,
} from "@/types";
import { mulberry32, sleep, uid } from "@/lib/utils";
import {
  seedGroups,
  seedKeys,
  seedLogs,
  seedModels,
  seedPlans,
  seedProviders,
  seedRoutes,
  seedSettings,
  seedUsers,
} from "./seed";

function clone<T>(v: T): T {
  return structuredClone(v);
}

const state = {
  providers: clone(seedProviders),
  models: clone(seedModels),
  routes: clone(seedRoutes),
  keys: clone(seedKeys),
  logs: clone(seedLogs),
  users: clone(seedUsers),
  groups: clone(seedGroups),
  plans: clone(seedPlans),
  settings: clone(seedSettings),
};

function providerName(id: string) {
  return state.providers.find((p) => p.id === id)?.name ?? id;
}

function maskKey(full: string) {
  return `${full.slice(0, 8)}••••••••${full.slice(-4)}`;
}

function fakeFullKey() {
  const rand = Math.random().toString(36).slice(2, 14);
  return `ug_live_${rand}${Math.random().toString(36).slice(2, 10)}`;
}

function seriesFor(range: TimeRange, seed = 11, from?: string, to?: string): TimePoint[] {
  const rand = mulberry32(seed + range.length);
  const points: TimePoint[] = [];
  const now = Date.now();

  if (range === "custom" && from && to) {
    const start = new Date(`${from}T00:00:00`).getTime();
    const end = new Date(`${to}T23:59:59`).getTime();
    const span = Math.max(1, Math.round((end - start) / 86_400_000));
    const stepDays = span > 40 ? Math.ceil(span / 30) : 1;
    for (let d = 0; d <= span; d += stepDays) {
      const day = new Date(start + d * 86_400_000);
      const wave = 0.55 + 0.45 * Math.sin(d / 3.4);
      const requests = Math.round(2400 * wave * (0.75 + rand()));
      const tokens = Math.round(requests * (920 + rand() * 1400));
      const cost = Number((tokens / 1e6 * (3.8 + rand() * 2.2)).toFixed(2));
      points.push({
        t: day.toISOString().slice(5, 10),
        requests,
        tokens,
        cost: Math.max(1.2, cost),
        latency: Math.round(480 + rand() * 520),
        errors: Math.round(requests * (0.008 + rand() * 0.02)),
      });
    }
    return points;
  }

  const hours = range === "today" ? 24 : range === "7d" ? 7 * 24 : 30 * 24;
  const step = range === "today" ? 1 : range === "7d" ? 6 : 24;
  for (let i = hours; i >= 0; i -= step) {
    const hour = new Date(now - i * 3600_000);
    const wave = 0.55 + 0.45 * Math.sin((hours - i) / (range === "today" ? 3.2 : 8));
    const requests = Math.round((range === "today" ? 980 : 2400) * wave * (0.75 + rand()));
    const tokens = Math.round(requests * (920 + rand() * 1400));
    const cost = Number((tokens / 1e6 * (3.8 + rand() * 2.2)).toFixed(2));
    const latency = Math.round(480 + rand() * 520 + (wave < 0.7 ? 180 : 0));
    const errors = Math.round(requests * (0.008 + rand() * 0.02));
    points.push({
      t: range === "30d" ? hour.toISOString().slice(5, 10) : hour.toISOString().slice(11, 16),
      requests,
      tokens,
      cost: Math.max(1.2, cost),
      latency,
      errors,
    });
  }
  return points;
}

function applyStrategy(r: RoutePolicy, strategy: RouteStrategy) {
  r.strategy = strategy;
  if (strategy === "cheapest") {
    r.targets = [...r.targets].sort((a, b) => a.inputPrice - b.inputPrice);
    const total = r.targets.length;
    r.targets.forEach((t, i) => {
      t.priority = i + 1;
      t.weight = i === 0 ? 70 : Math.round(30 / Math.max(1, total - 1));
    });
  }
  if (strategy === "fastest") {
    r.targets = [...r.targets].sort((a, b) => a.avgLatency - b.avgLatency);
    r.targets.forEach((t, i) => {
      t.priority = i + 1;
      t.weight = i === 0 ? 70 : 15;
    });
  }
  if (strategy === "stable") {
    r.targets = [...r.targets].sort((a, b) => b.successRate - a.successRate);
    r.targets.forEach((t, i) => {
      t.priority = i + 1;
      t.weight = i === 0 ? 80 : 10;
    });
  }
  if (strategy === "failover") {
    r.targets.forEach((t, i) => {
      t.priority = i + 1;
      t.weight = i === 0 ? 100 : 0;
    });
  }
  if (strategy === "random") {
    const w = Math.round(100 / Math.max(1, r.targets.length));
    r.targets.forEach((t, i) => {
      t.weight = w;
      t.priority = i + 1;
    });
  }
}

function targetFromProvider(id: string): RouteTarget {
  const p = state.providers.find((x) => x.id === id);
  return {
    providerId: id,
    weight: 10,
    priority: 9,
    successRate: p?.successRate ?? 0.98,
    avgLatency: p?.avgLatency ?? 800,
    inputPrice: 2,
    outputPrice: 8,
    health: p?.health ?? "healthy",
  };
}

export const mockDb = {
  async listProviders() {
    await sleep(80);
    return clone(state.providers);
  },
  async createProvider(input: ProviderInput): Promise<Provider> {
    await sleep(160);
    const item: Provider = {
      id: uid("prv"),
      name: input.name,
      type: input.type,
      baseUrl: input.baseUrl,
      balance: 128.4 + Math.random() * 80,
      modelCount: 6,
      todayCalls: 126 + Math.round(Math.random() * 40),
      successRate: 0.986,
      avgLatency: 640,
      priority: input.priority,
      weight: input.weight,
      health: "healthy",
      enabled: true,
      createdAt: new Date().toISOString(),
    };
    state.providers.unshift(item);
    return clone(item);
  },
  async updateProvider(id: string, patch: Partial<ProviderInput & { enabled: boolean; health: Provider["health"] }>) {
    await sleep(120);
    const p = state.providers.find((x) => x.id === id);
    if (!p) throw new Error("provider not found");
    Object.assign(p, patch);
    if (patch.enabled === false) p.health = "disabled";
    if (patch.enabled === true && p.health === "disabled") p.health = "healthy";
    return clone(p);
  },
  async deleteProvider(id: string) {
    await sleep(100);
    state.providers = state.providers.filter((p) => p.id !== id);
  },
  async toggleProvider(id: string) {
    const p = state.providers.find((x) => x.id === id);
    if (!p) throw new Error("provider not found");
    return this.updateProvider(id, { enabled: !p.enabled });
  },
  async testProvider(id: string): Promise<ProviderTestResult> {
    await sleep(520);
    const p = state.providers.find((x) => x.id === id);
    if (!p) return { ok: false, latency: 0, message: "渠道不存在" };
    if (!p.enabled) return { ok: false, latency: 0, message: "渠道已禁用" };
    if (p.health === "error") return { ok: false, latency: 1860, message: "上游返回 502" };
    return { ok: true, latency: Math.round(p.avgLatency * (0.8 + Math.random() * 0.3)), message: "连通正常" };
  },
  async pullModels(id: string) {
    await sleep(420);
    const p = state.providers.find((x) => x.id === id);
    if (!p) throw new Error("provider not found");
    p.modelCount += 1;
    return { count: p.modelCount };
  },
  async queryBalance(id: string): Promise<BalanceResult> {
    await sleep(360);
    const p = state.providers.find((x) => x.id === id);
    if (!p) throw new Error("provider not found");
    p.balance = Number((p.balance * (0.99 + Math.random() * 0.02)).toFixed(2));
    return { balance: p.balance, currency: "USD" };
  },

  async listModels() {
    await sleep(70);
    return clone(state.models);
  },
  async createModel(input: ModelInput): Promise<Model> {
    await sleep(140);
    const item: Model = {
      id: uid("mdl"),
      name: input.name,
      providerId: input.providerId,
      alias: input.alias,
      inputPrice: input.inputPrice,
      outputPrice: input.outputPrice,
      context: input.context,
      capabilities: input.capabilities,
      status: input.status ?? "active",
      preferredProviderId: input.preferredProviderId || input.providerId,
      todayCalls: 128 + Math.round(Math.random() * 80),
    };
    state.models.unshift(item);
    return clone(item);
  },
  async updateModel(id: string, patch: Partial<ModelInput & { status: Model["status"] }>): Promise<Model> {
    await sleep(120);
    const m = state.models.find((x) => x.id === id);
    if (!m) throw new Error("model not found");
    Object.assign(m, patch);
    return clone(m);
  },
  async deleteModel(id: string) {
    await sleep(100);
    state.models = state.models.filter((m) => m.id !== id);
  },

  async listRoutes() {
    await sleep(70);
    return clone(state.routes);
  },
  async updateRoute(id: string, patch: RoutePatch | RouteStrategy): Promise<RoutePolicy> {
    await sleep(80);
    const r = state.routes.find((x) => x.id === id);
    if (!r) throw new Error("route not found");
    const next: RoutePatch = typeof patch === "string" ? { strategy: patch } : patch;
    if (next.targets) {
      r.targets = clone(next.targets).map((t, i) => ({ ...t, priority: t.priority || i + 1 }));
    }
    if (next.strategy) applyStrategy(r, next.strategy);
    return clone(r);
  },
  async addRouteTarget(id: string, providerId: string): Promise<RoutePolicy> {
    await sleep(80);
    const r = state.routes.find((x) => x.id === id);
    if (!r) throw new Error("route not found");
    if (r.targets.some((t) => t.providerId === providerId)) return clone(r);
    r.targets.push(targetFromProvider(providerId));
    r.targets.forEach((t, i) => {
      t.priority = i + 1;
    });
    r.strategy = "custom";
    return clone(r);
  },
  async removeRouteTarget(id: string, providerId: string): Promise<RoutePolicy> {
    await sleep(80);
    const r = state.routes.find((x) => x.id === id);
    if (!r) throw new Error("route not found");
    if (r.targets.length <= 1) return clone(r);
    r.targets = r.targets.filter((t) => t.providerId !== providerId);
    r.targets.forEach((t, i) => {
      t.priority = i + 1;
    });
    r.strategy = "custom";
    return clone(r);
  },

  async listKeys() {
    await sleep(70);
    return clone(state.keys);
  },
  async createKey(input: ApiKeyInput): Promise<CreatedApiKey> {
    await sleep(180);
    const fullKey = fakeFullKey();
    const item: ApiKey = {
      id: uid("key"),
      name: input.name,
      maskedKey: maskKey(fullKey),
      owner: input.owner,
      allowedModels: input.allowedModels.length ? input.allowedModels : ["*"],
      used: 12.4,
      budget: input.budget,
      rpm: input.rpm,
      tpm: input.tpm,
      createdAt: new Date().toISOString(),
      expiresAt: input.expiresAt,
      status: "active",
    };
    state.keys.unshift(item);
    return { ...clone(item), fullKey };
  },
  async disableKey(id: string) {
    await sleep(100);
    const k = state.keys.find((x) => x.id === id);
    if (!k) throw new Error("key not found");
    k.status = k.status === "active" ? "disabled" : "active";
    return clone(k);
  },
  async deleteKey(id: string) {
    await sleep(100);
    state.keys = state.keys.filter((k) => k.id !== id);
  },
  async regenerateKey(id: string): Promise<CreatedApiKey> {
    await sleep(160);
    const k = state.keys.find((x) => x.id === id);
    if (!k) throw new Error("key not found");
    const fullKey = fakeFullKey();
    k.maskedKey = maskKey(fullKey);
    k.status = "active";
    return { ...clone(k), fullKey };
  },

  async listLogs(query: LogQuery = {}): Promise<Paged<RequestLog>> {
    await sleep(90);
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 12;
    let items = state.logs;
    if (query.q) {
      const q = query.q.toLowerCase();
      items = items.filter(
        (l) =>
          l.requestId.toLowerCase().includes(q) ||
          l.user.includes(q) ||
          l.model.includes(q) ||
          l.keyName.toLowerCase().includes(q),
      );
    }
    if (query.model && query.model !== "all") items = items.filter((l) => l.model === query.model);
    if (query.providerId && query.providerId !== "all") items = items.filter((l) => l.providerId === query.providerId);
    if (query.keyId && query.keyId !== "all") items = items.filter((l) => l.keyId === query.keyId);
    if (query.status && query.status !== "all") items = items.filter((l) => l.status === query.status);
    const total = items.length;
    const slice = items.slice((page - 1) * pageSize, page * pageSize);
    return { items: clone(slice), total, page, pageSize };
  },

  async getDashboard(): Promise<DashboardSnapshot> {
    await sleep(90);
    const series = seriesFor("today", 3);
    const todayRequests = series.reduce((s, p) => s + p.requests, 0);
    const todayTokens = series.reduce((s, p) => s + p.tokens, 0);
    const todayCost = series.reduce((s, p) => s + p.cost, 0);
    const online = state.providers.filter((p) => p.enabled && p.health !== "error" && p.health !== "disabled").length;
    return {
      todayRequests,
      todayTokens,
      todayCost,
      successRate: 0.986,
      avgLatency: 704,
      activeKeys: state.keys.filter((k) => k.status === "active").length,
      onlineProviders: online,
      deltas: { requests: 0.128, tokens: 0.094, cost: 0.072, successRate: -0.004, latency: -0.061 },
      series,
      modelRank: [...state.models]
        .sort((a, b) => b.todayCalls - a.todayCalls)
        .slice(0, 6)
        .map((m) => ({ id: m.id, name: m.alias, value: m.todayCalls, extra: providerName(m.providerId) })),
      providerHealth: state.providers.map((p) => ({
        id: p.id,
        name: p.name,
        health: p.health,
        successRate: p.successRate,
        latency: p.avgLatency,
      })),
      recentLogs: clone(state.logs.slice(0, 8)),
      alerts: [
        {
          id: "al-1",
          severity: "error",
          title: "New API B 连续失败",
          detail: "近 15 分钟错误率 18.8%，已从 claude-sonnet 主路径摘除。",
          time: new Date(Date.now() - 9 * 60_000).toISOString(),
        },
        {
          id: "al-2",
          severity: "warning",
          title: "Gemini 延迟升高",
          detail: "P95 从 1.1s 升至 1.9s，failover 已切到 OpenRouter。",
          time: new Date(Date.now() - 26 * 60_000).toISOString(),
        },
      ],
    };
  },

  async listUsers() {
    await sleep(60);
    return { users: clone(state.users), groups: clone(state.groups), plans: clone(state.plans) };
  },
  async createUser(input: UserInput): Promise<User> {
    await sleep(140);
    const item: User = {
      id: uid("usr"),
      name: input.name,
      email: input.email,
      role: input.role,
      groupId: input.groupId,
      planId: input.planId,
      balance: input.balance,
      spend: 24.8,
      keyCount: 1,
      requestCount: 860,
      status: "active",
    };
    state.users.unshift(item);
    const g = state.groups.find((x) => x.id === input.groupId);
    if (g) g.memberCount += 1;
    return clone(item);
  },
  async updateUser(id: string, patch: Partial<UserInput & { status: User["status"] }>): Promise<User> {
    await sleep(120);
    const u = state.users.find((x) => x.id === id);
    if (!u) throw new Error("user not found");
    Object.assign(u, patch);
    return clone(u);
  },

  async getAnalytics(query: AnalyticsQuery | TimeRange): Promise<AnalyticsSnapshot> {
    await sleep(110);
    const range = typeof query === "string" ? query : query.range;
    const from = typeof query === "string" ? undefined : query.from;
    const to = typeof query === "string" ? undefined : query.to;
    const series = seriesFor(range, 21, from, to);
    const requests = series.reduce((s, p) => s + p.requests, 0);
    const tokens = series.reduce((s, p) => s + p.tokens, 0);
    const cost = series.reduce((s, p) => s + p.cost, 0);
    const latency = Math.round(series.reduce((s, p) => s + p.latency, 0) / series.length);
    const errors = series.reduce((s, p) => s + p.errors, 0);
    const models = [...state.models].sort((a, b) => b.todayCalls - a.todayCalls);
    return {
      range,
      totals: { requests, tokens, cost, latency, errorRate: errors / Math.max(1, requests) },
      series,
      modelDistribution: models.slice(0, 6).map((m) => ({ name: m.alias, value: m.todayCalls })),
      providerDistribution: state.providers
        .filter((p) => p.enabled)
        .map((p) => ({ name: p.name, value: Math.max(860, p.todayCalls) })),
      ranks: {
        expensiveModels: [...state.models]
          .map((m) => ({ id: m.id, name: m.alias, value: m.outputPrice || m.inputPrice, extra: `$${m.inputPrice}/${m.outputPrice}` }))
          .sort((a, b) => b.value - a.value)
          .slice(0, 5),
        popularModels: models.slice(0, 5).map((m) => ({ id: m.id, name: m.alias, value: m.todayCalls })),
        slowestProviders: [...state.providers]
          .sort((a, b) => b.avgLatency - a.avgLatency)
          .slice(0, 5)
          .map((p) => ({ id: p.id, name: p.name, value: p.avgLatency })),
        failingProviders: [...state.providers]
          .sort((a, b) => a.successRate - b.successRate)
          .slice(0, 5)
          .map((p) => ({ id: p.id, name: p.name, value: 1 - p.successRate })),
        topKeys: [...state.keys]
          .sort((a, b) => b.used - a.used)
          .slice(0, 5)
          .map((k) => ({ id: k.id, name: k.name, value: k.used })),
      },
    };
  },

  async getMonitor(): Promise<MonitorEndpoint[]> {
    await sleep(80);
    const rand = mulberry32(88);
    return state.providers.map((p) => ({
      providerId: p.id,
      name: p.name,
      endpoint: p.baseUrl,
      health: p.health,
      successRate: p.successRate,
      p50: Math.round(p.avgLatency * 0.72),
      p95: Math.round(p.avgLatency * 1.55),
      p99: Math.round(p.avgLatency * 2.2),
      errorRate: 1 - p.successRate,
      uptime: Array.from({ length: 24 }, (_, i) => {
        if (!p.enabled) return 0;
        if (p.health === "error") return rand() > 0.45 ? 0 : 1;
        if (p.health === "degraded") return i % 7 === 3 ? 0.5 : 1;
        return rand() > 0.97 ? 0.5 : 1;
      }),
    }));
  },

  async getSettings() {
    await sleep(40);
    return clone(state.settings);
  },
  async saveSettings(next: SettingsState) {
    await sleep(120);
    state.settings = clone(next);
    return clone(state.settings);
  },
};

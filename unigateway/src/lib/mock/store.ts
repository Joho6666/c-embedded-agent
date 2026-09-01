"use client";

import type {
  AnalyticsSnapshot,
  ApiKey,
  ApiKeyInput,
  BalanceResult,
  CreatedApiKey,
  DashboardSnapshot,
  LogQuery,
  MonitorEndpoint,
  Paged,
  Provider,
  ProviderInput,
  ProviderTestResult,
  RequestLog,
  RoutePolicy,
  RouteStrategy,
  SettingsState,
  TimePoint,
  TimeRange,
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

function seriesFor(range: TimeRange, seed = 11): TimePoint[] {
  const rand = mulberry32(seed + range.length);
    const hours = range === "today" ? 24 : range === "7d" ? 7 * 24 : range === "custom" ? 14 * 24 : 30 * 24;
    const step = range === "today" ? 1 : range === "7d" ? 6 : range === "custom" ? 12 : 24;
  const points: TimePoint[] = [];
  const now = Date.now();
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

  async listRoutes() {
    await sleep(70);
    return clone(state.routes);
  },
  async updateRoute(id: string, strategy: RouteStrategy): Promise<RoutePolicy> {
    await sleep(140);
    const r = state.routes.find((x) => x.id === id);
    if (!r) throw new Error("route not found");
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
      const w = Math.round(100 / r.targets.length);
      r.targets.forEach((t, i) => {
        t.weight = w;
        t.priority = i + 1;
      });
    }
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

  async getAnalytics(range: TimeRange): Promise<AnalyticsSnapshot> {
    await sleep(110);
    const series = seriesFor(range, 21);
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

  async listUsers() {
    await sleep(60);
    return { users: clone(state.users), groups: clone(state.groups), plans: clone(state.plans) };
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

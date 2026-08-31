import type { OverviewMetrics, TrafficShare, UsageRange, UsageSlice } from "@/types";
import { mulberry32 } from "@/lib/utils";
import { providers } from "./providers";

export const overviewMetrics: OverviewMetrics = {
  requestsToday: 128_421,
  tokensToday: 824_000_000,
  estimatedCost: 42.18,
  successRate: 99.42,
  avgTtftMs: 620,
  avgLatencyMs: 890,
  activeProviders: 12,
  healthyCredentials: 18,
  circuitOpen: 3,
  availableModels: 48,
  rpm: 128,
  activeClients: 5,
};

export const trafficShare: TrafficShare[] = [
  { providerId: "openai", name: "OpenAI", pct: 35, color: "#10a37f" },
  { providerId: "gemini", name: "Gemini", pct: 25, color: "#4285f4" },
  { providerId: "anthropic", name: "Claude", pct: 18, color: "#d97757" },
  { providerId: "glm", name: "GLM", pct: 12, color: "#165dff" },
  { providerId: "kimi", name: "Kimi", pct: 6, color: "#f5c518" },
  { providerId: "others", name: "Others", pct: 4, color: "#71717a" },
];

function points(n: number, seed: number, scale: number) {
  const rnd = mulberry32(seed);
  const out = [];
  const now = Date.now();
  for (let i = n - 1; i >= 0; i--) {
    const t = new Date(now - i * (n > 30 ? 24 : n > 24 ? 60 : 30) * 60_000);
    const wave = 0.65 + Math.sin(i / 3.2) * 0.18 + rnd() * 0.2;
    out.push({
      t: n > 30 ? t.toISOString().slice(5, 10) : t.toISOString().slice(11, 16),
      requests: Math.round(4200 * scale * wave),
      tokens: Math.round(28_000_000 * scale * wave),
      cost: Number((1.4 * scale * wave).toFixed(2)),
      errors: Math.round(18 * scale * (0.4 + rnd())),
      latency: Math.round(720 + rnd() * 280),
    });
  }
  return out;
}

function slice(range: UsageRange, n: number, seed: number, scale: number, totals: UsageSlice["totals"]): UsageSlice {
  return {
    range,
    totals,
    trend: points(n, seed, scale),
    byProvider: [
      { id: "openai", name: "OpenAI", value: 35, color: "#10a37f" },
      { id: "gemini", name: "Gemini", value: 25, color: "#4285f4" },
      { id: "anthropic", name: "Claude", value: 18, color: "#d97757" },
      { id: "glm", name: "GLM", value: 12, color: "#165dff" },
      { id: "kimi", name: "Kimi", value: 6, color: "#f5c518" },
      { id: "others", name: "Others", value: 4, color: "#71717a" },
    ],
    byModel: [
      { id: "coding", name: "coding", value: 28 },
      { id: "fast", name: "fast", value: 22 },
      { id: "smart", name: "smart", value: 16 },
      { id: "cheap", name: "cheap", value: 12 },
      { id: "coding-pro", name: "coding-pro", value: 9 },
      { id: "long-context", name: "long-context", value: 7 },
      { id: "vision", name: "vision", value: 4 },
      { id: "reasoning", name: "reasoning", value: 2 },
    ],
    byCredential: providers.slice(0, 8).map((p, i) => ({
      id: p.id,
      name: p.name,
      value: [22, 18, 14, 12, 9, 8, 7, 10][i],
    })),
    byKey: [
      { id: "key_wb", name: "WorkBuddy", value: 33 },
      { id: "key_oc", name: "OpenCode", value: 17 },
      { id: "key_srv", name: "Server", value: 15 },
      { id: "key_myos", name: "MyOS", value: 14 },
      { id: "key_desk", name: "Laptop", value: 10 },
      { id: "key_auto", name: "Automation", value: 6 },
      { id: "key_cc", name: "Claude Code", value: 3 },
      { id: "key_vs", name: "VS Code Agent", value: 2 },
    ],
    errors: [
      { name: "429", value: 42 },
      { name: "5xx", value: 18 },
      { name: "Timeout", value: 11 },
      { name: "401", value: 6 },
      { name: "Quota", value: 5 },
      { name: "Other", value: 4 },
    ],
  };
}

export const usageByRange: Record<UsageRange, UsageSlice> = {
  today: slice("today", 24, 7, 1, {
    requests: 128_421,
    tokens: 824_000_000,
    inputTokens: 512_000_000,
    outputTokens: 268_000_000,
    cachedTokens: 44_000_000,
    cost: 42.18,
    successRate: 99.42,
    errorRate: 0.58,
    latency: 890,
    ttft: 620,
  }),
  "24h": slice("24h", 24, 9, 1.05, {
    requests: 136_880,
    tokens: 861_000_000,
    inputTokens: 534_000_000,
    outputTokens: 281_000_000,
    cachedTokens: 46_000_000,
    cost: 44.9,
    successRate: 99.31,
    errorRate: 0.69,
    latency: 910,
    ttft: 635,
  }),
  "7d": slice("7d", 7, 11, 6.8, {
    requests: 812_400,
    tokens: 5_210_000_000,
    inputTokens: 3_240_000_000,
    outputTokens: 1_680_000_000,
    cachedTokens: 290_000_000,
    cost: 268.4,
    successRate: 99.18,
    errorRate: 0.82,
    latency: 905,
    ttft: 640,
  }),
  "30d": slice("30d", 30, 13, 28, {
    requests: 3_412_000,
    tokens: 21_800_000_000,
    inputTokens: 13_400_000_000,
    outputTokens: 7_100_000_000,
    cachedTokens: 1_300_000_000,
    cost: 1124.6,
    successRate: 99.05,
    errorRate: 0.95,
    latency: 940,
    ttft: 655,
  }),
};

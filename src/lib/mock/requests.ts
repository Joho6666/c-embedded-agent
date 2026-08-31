import type { RequestLog, RequestStatusCode, TraceEvent } from "@/types";
import { mulberry32 } from "@/lib/utils";
import { apiKeys } from "./keys";
import { virtualModels } from "./virtual";
import { credentials } from "./credentials";
import { realModels } from "./models";
import { providers } from "./providers";

const STATUSES: RequestStatusCode[] = [
  200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200,
  200, 200, 200, 200, 200, 429, 429, 500, 502, 400, 401, 403, "timeout", "quota_exhausted",
  "circuit_open", "disabled",
];

function pad(n: number) {
  return String(n).padStart(2, "0");
}

function clock(d: Date) {
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

export function buildRequests(count = 300): RequestLog[] {
  const rnd = mulberry32(42);
  const now = Date.now();
  const logs: RequestLog[] = [];
  const liveKeys = apiKeys.filter((k) => k.status === "active");

  for (let i = 0; i < count; i++) {
    const vm = virtualModels[Math.floor(rnd() * virtualModels.length)];
    const cand = vm.candidates[Math.floor(rnd() * vm.candidates.length)];
    const model = realModels.find((m) => m.id === cand.modelId)!;
    const cred = credentials.find((c) => c.id === cand.credentialId) ?? credentials[0];
    const key = liveKeys[Math.floor(rnd() * liveKeys.length)];
    let status = STATUSES[Math.floor(rnd() * STATUSES.length)];
    if (cred.status === "circuit_open") status = rnd() > 0.3 ? "circuit_open" : 502;
    if (cred.status === "unauthorized") status = 401;
    if (cred.status === "disabled") status = "disabled";
    if (cred.status === "quota_exhausted") status = rnd() > 0.4 ? "quota_exhausted" : 429;
    if (cred.status === "rate_limited" && rnd() > 0.5) status = 429;

    const t = new Date(now - Math.floor(rnd() * 16 * 3600_000) - i * 12_000);
    const inputTokens = Math.floor(180 + rnd() * 4200);
    const outputTokens = Math.floor(40 + rnd() * 1800);
    const cachedTokens = rnd() > 0.7 ? Math.floor(inputTokens * 0.4) : 0;
    const ttft = Math.floor(model.ttftMs * (0.7 + rnd() * 0.8));
    const latency = ttft + Math.floor(200 + rnd() * 1800);
    const fallback = status === 429 || status === 500 || status === 502 || status === "timeout";
    const retries = fallback ? 1 + Math.floor(rnd() * 2) : 0;
    const fallbackCount = fallback ? 1 : 0;
    const ok = status === 200;
    const cost = ((inputTokens * model.inputPrice + outputTokens * model.outputPrice) / 1_000_000) * (ok ? 1 : 0.15);

    let usedCred = cred;
    let usedModel = model;
    let usedProvider = model.providerId;
    if (fallback) {
      const next = vm.candidates.find((c) => c.credentialId !== cred.id) ?? vm.candidates[0];
      const nm = realModels.find((m) => m.id === next.modelId) ?? model;
      const nc = credentials.find((c) => c.id === next.credentialId) ?? cred;
      usedCred = nc;
      usedModel = nm;
      usedProvider = nm.providerId;
    }

    const callId = `req_${t.getTime().toString(36)}_${i.toString(36)}`;
    const trace: TraceEvent[] = [
      { at: clock(t), label: "Request received", kind: "info", detail: `${key.name} → ${vm.slug}` },
      { at: clock(t), label: `Selected virtual model: ${vm.slug}`, kind: "info" },
      {
        at: clock(t),
        label: `Router selected ${providers.find((p) => p.id === cred.providerId)?.name} / ${cred.name}`,
        kind: "info",
      },
    ];
    if (fallback) {
      trace.push({
        at: clock(new Date(t.getTime() + 400)),
        label: String(status).toUpperCase(),
        kind: "error",
        detail: cred.lastError ?? `upstream ${status}`,
      });
      trace.push({ at: clock(new Date(t.getTime() + 420)), label: "Retry / Fallback", kind: "warn" });
      trace.push({
        at: clock(new Date(t.getTime() + 450)),
        label: `Selected ${usedCred.name}`,
        kind: "info",
      });
      trace.push({
        at: clock(new Date(t.getTime() + latency)),
        label: "200 OK",
        kind: "ok",
        detail: usedModel.modelId,
      });
      status = 200;
    } else if (ok) {
      trace.push({
        at: clock(new Date(t.getTime() + 80)),
        label: "Request sent",
        kind: "info",
        detail: model.modelId,
      });
      trace.push({
        at: clock(new Date(t.getTime() + latency)),
        label: "200 OK · Response streamed",
        kind: "ok",
      });
    } else {
      trace.push({
        at: clock(new Date(t.getTime() + 120)),
        label: String(status).toUpperCase(),
        kind: "error",
        detail: cred.lastError ?? "upstream error",
      });
    }

    logs.push({
      id: callId,
      callId,
      time: t.toISOString(),
      clientKeyId: key.id,
      virtualModel: vm.slug,
      realModel: usedModel.modelId,
      providerId: usedProvider,
      credentialId: usedCred.id,
      status,
      inputTokens,
      outputTokens,
      cachedTokens,
      ttftMs: ttft,
      latencyMs: latency,
      retries,
      fallbackCount,
      cost,
      stream: rnd() > 0.25,
      error: ok ? undefined : String(status),
      trace,
    });
  }

  return logs.sort((a, b) => +new Date(b.time) - +new Date(a.time));
}

export const requestLogs = buildRequests(300);

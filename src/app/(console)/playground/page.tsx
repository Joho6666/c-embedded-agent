"use client";

import { useState } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useGateway } from "@/lib/stores/gateway";
import { formatMs, formatUsd } from "@/lib/format";
import { uid } from "@/lib/utils";
import type { RequestLog, TraceEvent } from "@/types";

const SAMPLE =
  "You are a coding agent. Explain how to implement a weighted failover router for LLM providers in 6 bullets.";

export default function PlaygroundPage() {
  const vms = useGateway((s) => s.virtualModels);
  const models = useGateway((s) => s.models);
  const prepend = useGateway((s) => s.prependLog);
  const [vm, setVm] = useState("coding");
  const [real, setReal] = useState("auto");
  const [system, setSystem] = useState("You are Universal AI Gateway Playground.");
  const [message, setMessage] = useState(SAMPLE);
  const [temp, setTemp] = useState([0.2]);
  const [maxTokens, setMaxTokens] = useState([800]);
  const [stream, setStream] = useState(true);
  const [tools, setTools] = useState(true);
  const [jsonMode, setJsonMode] = useState(false);
  const [running, setRunning] = useState(false);
  const [output, setOutput] = useState("");
  const [meta, setMeta] = useState<{
    provider: string;
    credential: string;
    model: string;
    route: string[];
    ttft: number;
    latency: number;
    inTok: number;
    outTok: number;
    cost: number;
  } | null>(null);

  async function send() {
    setRunning(true);
    setOutput("");
    const route = [
      "coding → OpenAI Credential A",
      "HTTP 429 rate_limit_exceeded",
      "Fallback",
      "Claude Production",
      "200 OK",
    ];
    setMeta({
      provider: "Anthropic",
      credential: "Claude Production",
      model: "claude-sonnet-4",
      route,
      ttft: 620,
      latency: 1840,
      inTok: 412,
      outTok: 286,
      cost: 0.0124,
    });
    const text = stream
      ? "coding → OpenAI 429 → Claude Success.\n\n1. Treat Virtual Model as an alias, never a vendor id.\n2. Score candidates by health, remaining quota, and weight.\n3. On 429, immediately switch credential in the same provider pool.\n4. On 401, disable the credential and fail over.\n5. After 5 consecutive failures, open the circuit.\n6. Stream only after the first hop commits, or buffer for in-band failover."
      : "Non-stream response: failover completed via Claude Production.";
    if (stream) {
      for (const ch of text) {
        setOutput((s) => s + ch);
        await new Promise((r) => setTimeout(r, 8));
      }
    } else {
      await new Promise((r) => setTimeout(r, 400));
      setOutput(text);
    }
    const now = new Date();
    const trace: TraceEvent[] = [
      { at: now.toLocaleTimeString("zh-CN", { hour12: false }), label: "Request received", kind: "info" },
      { at: now.toLocaleTimeString("zh-CN", { hour12: false }), label: `Selected virtual model: ${vm}`, kind: "info" },
      { at: now.toLocaleTimeString("zh-CN", { hour12: false }), label: "Selected OpenAI Credential A", kind: "info" },
      { at: now.toLocaleTimeString("zh-CN", { hour12: false }), label: "429 Rate Limited", kind: "error" },
      { at: now.toLocaleTimeString("zh-CN", { hour12: false }), label: "Fallback", kind: "warn" },
      { at: now.toLocaleTimeString("zh-CN", { hour12: false }), label: "Selected Claude Production", kind: "info" },
      { at: now.toLocaleTimeString("zh-CN", { hour12: false }), label: "200 OK", kind: "ok" },
    ];
    const log: RequestLog = {
      id: uid("req"),
      callId: uid("req"),
      time: now.toISOString(),
      clientKeyId: "key_desk",
      virtualModel: vm,
      realModel: "claude-sonnet-4",
      providerId: "anthropic",
      credentialId: "cred_an_a",
      status: 200,
      inputTokens: 412,
      outputTokens: 286,
      cachedTokens: 0,
      ttftMs: 620,
      latencyMs: 1840,
      retries: 1,
      fallbackCount: 1,
      cost: 0.0124,
      stream,
      trace,
    };
    prepend(log);
    setRunning(false);
  }

  return (
    <div>
      <PageHeader title="API Playground" description="模拟一次真实 Gateway 调用，包含 429 与 Fallback。" />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="space-y-3 rounded-md border border-border bg-card p-3">
          <div className="grid grid-cols-2 gap-2">
            <div className="grid gap-1">
              <Label>Virtual Model</Label>
              <Select value={vm} onValueChange={setVm}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {vms.map((v) => (
                    <SelectItem key={v.id} value={v.slug}>
                      {v.slug}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1">
              <Label>Real Model override</Label>
              <Select value={real} onValueChange={setReal}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">auto (router)</SelectItem>
                  {models.slice(0, 20).map((m) => (
                    <SelectItem key={m.id} value={m.modelId}>
                      {m.modelId}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid gap-1">
            <Label>System Prompt</Label>
            <Textarea value={system} onChange={(e) => setSystem(e.target.value)} />
          </div>
          <div className="grid gap-1">
            <Label>Messages</Label>
            <Textarea className="min-h-32" value={message} onChange={(e) => setMessage(e.target.value)} />
          </div>
          <div>
            <Label>Temperature {temp[0].toFixed(2)}</Label>
            <Slider min={0} max={2} step={0.05} value={temp} onValueChange={setTemp} />
          </div>
          <div>
            <Label>Max Tokens {maxTokens[0]}</Label>
            <Slider min={64} max={4096} step={64} value={maxTokens} onValueChange={setMaxTokens} />
          </div>
          <div className="flex flex-wrap gap-4 text-[12px]">
            <label className="flex items-center gap-2">
              <Switch checked={stream} onCheckedChange={setStream} /> Streaming
            </label>
            <label className="flex items-center gap-2">
              <Switch checked={tools} onCheckedChange={setTools} /> Tools
            </label>
            <label className="flex items-center gap-2">
              <Switch checked={jsonMode} onCheckedChange={setJsonMode} /> JSON Mode
            </label>
          </div>
          <Button disabled={running} onClick={send}>
            {running ? "Running…" : "Send"}
          </Button>
        </div>
        <div className="rounded-md border border-border bg-card p-3">
          <div className="mb-2 text-[12px] font-medium">Response</div>
          <pre className="min-h-40 whitespace-pre-wrap rounded-sm border border-border bg-panel-2 p-2 font-mono text-[12px]">
            {output || "等待发送…"}
          </pre>
          {meta && (
            <div className="mt-3 grid grid-cols-2 gap-2 text-[12px]">
              <KV k="Provider" v={meta.provider} />
              <KV k="Credential" v={meta.credential} />
              <KV k="Actual Model" v={meta.model} />
              <KV k="TTFT" v={formatMs(meta.ttft)} />
              <KV k="Latency" v={formatMs(meta.latency)} />
              <KV k="Tokens" v={`${meta.inTok} / ${meta.outTok}`} />
              <KV k="Cost" v={formatUsd(meta.cost, 4)} />
              <KV k="Route" v={meta.route.join(" → ")} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <div className="rounded-sm border border-border px-2 py-1">
      <div className="text-[10px] text-muted-foreground">{k}</div>
      <div className="font-mono text-[11px]">{v}</div>
    </div>
  );
}

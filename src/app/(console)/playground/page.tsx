"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useGateway } from "@/lib/stores/gateway";
import { formatMs } from "@/lib/format";
import { gatewayApi } from "@/lib/services/gateway";
import { playgroundKey, setPlaygroundKey } from "@/lib/api/http";
import { toast } from "sonner";

const SAMPLE = "Reply with one short sentence: gateway playground ok.";

export default function PlaygroundPage() {
  const vms = useGateway((s) => s.virtualModels);
  const models = useGateway((s) => s.models);
  const providers = useGateway((s) => s.providers);
  const creds = useGateway((s) => s.credentials);
  const reloadLogs = useGateway((s) => s.reloadLogs);
  const [vm, setVm] = useState("");
  const [real, setReal] = useState("auto");
  const [system, setSystem] = useState("You are Universal AI Gateway Playground.");
  const [message, setMessage] = useState(SAMPLE);
  const [temp, setTemp] = useState([0.2]);
  const [maxTokens, setMaxTokens] = useState([256]);
  const [stream, setStream] = useState(true);
  const [running, setRunning] = useState(false);
  const [output, setOutput] = useState("");
  const [key, setKey] = useState("");
  const [meta, setMeta] = useState<{
    provider: string;
    credential: string;
    model: string;
    ttft: number;
    latency: number;
    inTok: number;
    outTok: number;
    status: string;
  } | null>(null);

  useEffect(() => {
    setKey(playgroundKey());
  }, []);
  useEffect(() => {
    if (!vm) {
      const first = vms[0]?.slug || models[0]?.modelId || "";
      if (first) setVm(first);
    }
  }, [vm, vms, models]);

  async function send() {
    if (!key) {
      toast.error("填写 Gateway API Key（sk-gw-…）");
      return;
    }
    setPlaygroundKey(key);
    setRunning(true);
    setOutput("");
    setMeta(null);
    const model = real === "auto" ? vm : real;
    const body = {
      model,
      stream,
      temperature: temp[0],
      max_tokens: maxTokens[0],
      messages: [
        { role: "system", content: system },
        { role: "user", content: message },
      ],
    };
    const started = performance.now();
    try {
      const res = await gatewayApi.chatCompletions(body, key);
      if (stream && res.body) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        let text = "";
        let ttft = 0;
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          if (!ttft) ttft = performance.now() - started;
          buf += decoder.decode(value, { stream: true });
          const parts = buf.split("\n\n");
          buf = parts.pop() ?? "";
          for (const part of parts) {
            const line = part.split("\n").find((l) => l.startsWith("data:"));
            if (!line) continue;
            const data = line.slice(5).trim();
            if (data === "[DONE]") continue;
            try {
              const json = JSON.parse(data);
              const piece = json.choices?.[0]?.delta?.content;
              if (piece) {
                text += piece;
                setOutput(text);
              }
            } catch {
              /* ignore parse */
            }
          }
        }
        const latency = performance.now() - started;
        setMeta({
          provider: "—",
          credential: "—",
          model,
          ttft: Math.round(ttft),
          latency: Math.round(latency),
          inTok: 0,
          outTok: 0,
          status: String(res.status),
        });
      } else {
        const json = await res.json();
        const text = json.choices?.[0]?.message?.content ?? json.error?.message ?? JSON.stringify(json);
        setOutput(typeof text === "string" ? text : JSON.stringify(text));
        const usage = json.usage || {};
        setMeta({
          provider: "—",
          credential: "—",
          model: json.model || model,
          ttft: Math.round(performance.now() - started),
          latency: Math.round(performance.now() - started),
          inTok: usage.prompt_tokens || 0,
          outTok: usage.completion_tokens || 0,
          status: String(res.status),
        });
      }
      await reloadLogs();
    } catch (e) {
      setOutput(e instanceof Error ? e.message : "request failed");
      toast.error("调用失败");
    } finally {
      setRunning(false);
    }
  }

  const last = useGateway((s) => s.logs[0]);

  return (
    <div>
      <PageHeader title="API Playground" description="真实调用 POST /v1/chat/completions，支持 SSE。" />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="space-y-3 rounded-md border border-border bg-card p-3">
          <div className="grid gap-1">
            <Label>Gateway API Key</Label>
            <Input
              type="password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="sk-gw-…"
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="grid gap-1">
              <Label>Model</Label>
              <Select value={vm} onValueChange={setVm}>
                <SelectTrigger>
                  <SelectValue placeholder="选择模型" />
                </SelectTrigger>
                <SelectContent>
                  {vms.map((v) => (
                    <SelectItem key={v.id} value={v.slug}>
                      {v.slug} (virtual)
                    </SelectItem>
                  ))}
                  {models.map((m) => (
                    <SelectItem key={m.id} value={m.modelId}>
                      {m.modelId}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1">
              <Label>Override</Label>
              <Select value={real} onValueChange={setReal}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">auto (router)</SelectItem>
                  {models.map((m) => (
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
          <label className="flex items-center gap-2 text-[12px]">
            <Switch checked={stream} onCheckedChange={setStream} /> Streaming
          </label>
          <Button disabled={running} onClick={() => void send()}>
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
              <KV k="Status" v={meta.status} />
              <KV k="Actual Model" v={meta.model} />
              <KV k="TTFT" v={formatMs(meta.ttft)} />
              <KV k="Latency" v={formatMs(meta.latency)} />
              <KV k="Tokens" v={`${meta.inTok} / ${meta.outTok}`} />
              <KV k="Requested" v={real === "auto" ? vm : real} />
            </div>
          )}
          {last && (
            <div className="mt-3 text-[12px] text-muted-foreground">
              Last log: {last.realModel || last.virtualModel} · {providers.find((p) => p.id === last.providerId)?.name} ·{" "}
              {creds.find((c) => c.id === last.credentialId)?.name} · fallback {last.fallbackCount}
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

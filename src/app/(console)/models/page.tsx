"use client";

import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useGateway } from "@/lib/stores/gateway";
import { CapabilityPills } from "@/components/common/CapabilityPills";
import { formatMs, formatPercent, formatUsd } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { gatewayApi, type ModelPricing } from "@/lib/services/gateway";
import { toast } from "sonner";

const chips = ["coding", "reasoning", "cheap", "fast", "vision", "agent", "long-context"];

export default function ModelsPage() {
  const models = useGateway((s) => s.models);
  const providers = useGateway((s) => s.providers);
  const [q, setQ] = useState("");
  const [tag, setTag] = useState<string>();

  const filtered = useMemo(() => {
    return models.filter((m) => {
      const p = providers.find((x) => x.id === m.providerId);
      const text = `${m.name} ${m.modelId} ${p?.name ?? ""} ${m.tags.join(" ")}`.toLowerCase();
      const hit = text.includes(q.toLowerCase());
      const tagHit = !tag || m.tags.includes(tag) || m.capabilities.includes(tag as never);
      return hit && tagHit;
    });
  }, [models, providers, q, tag]);

  return (
    <div>
      <PageHeader title="模型中心" description="所有真实模型。搜索 coding / reasoning / cheap / fast / vision / agent。" />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索模型" className="max-w-64" />
        {chips.map((c) => (
          <button
            key={c}
            onClick={() => setTag(tag === c ? undefined : c)}
            className={`rounded-sm border px-2 py-0.5 text-[11px] ${tag === c ? "border-foreground/40 bg-accent" : "border-border"}`}
          >
            {c}
          </button>
        ))}
      </div>
      <div className="overflow-auto rounded-md border border-border">
        <table className="gw-table w-full min-w-[1080px] text-left text-[12px]">
          <thead className="bg-muted/40 text-[11px] text-muted-foreground">
            <tr>
              {["Model", "Provider", "Model ID", "能力", "Context", "In / Out", "TTFT", "速度", "成功率", "Cred", "状态"].map(
                (h) => (
                  <th key={h} className="px-2 py-2 font-medium">
                    {h}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {filtered.map((m) => {
              const p = providers.find((x) => x.id === m.providerId);
              return (
                <tr key={m.id} className="border-t border-border">
                  <td className="px-2 py-2">{m.name}</td>
                  <td>{p?.name}</td>
                  <td className="font-mono text-[11px]">{m.modelId}</td>
                  <td>
                    <CapabilityPills items={m.capabilities} max={4} />
                  </td>
                  <td className="font-mono">{m.contextWindow ? m.contextWindow.toLocaleString() : "—"}</td>
                  <td className="font-mono">
                    {formatUsd(m.inputPrice, 2)} / {formatUsd(m.outputPrice, 2)}
                  </td>
                  <td className="font-mono">{formatMs(m.ttftMs)}</td>
                  <td className="font-mono">{m.tokensPerSec ? `${m.tokensPerSec} t/s` : "—"}</td>
                  <td className="font-mono">{formatPercent(m.successRate, 1)}</td>
                  <td className="font-mono">{m.credentialCount}</td>
                  <td>
                    <Badge tone={m.status === "available" ? "success" : m.status === "degraded" ? "warning" : "error"}>
                      {m.status}
                    </Badge>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="mt-2 text-[11px] text-muted-foreground">{filtered.length} models</div>
      <PricingBlock />
    </div>
  );
}

function PricingBlock() {
  const [rows, setRows] = useState<ModelPricing[]>([]);
  const [model, setModel] = useState("");
  const [provider, setProvider] = useState("");
  const [input, setInput] = useState("0");
  const [output, setOutput] = useState("0");

  const reload = () => {
    void gatewayApi.listPricing().then(setRows).catch(() => setRows([]));
  };

  useEffect(() => {
    reload();
  }, []);

  return (
    <div className="mt-6 rounded-lg border border-border bg-card p-3">
      <div className="mb-2 text-[13px] font-medium">Pricing</div>
      <p className="mb-3 text-[12px] text-muted-foreground">手动维护每百万 Token 价格。RequestLog 用此估算成本。</p>
      <div className="mb-3 flex flex-wrap gap-2">
        <Input value={provider} onChange={(e) => setProvider(e.target.value)} placeholder="provider" className="max-w-32" />
        <Input value={model} onChange={(e) => setModel(e.target.value)} placeholder="model" className="max-w-40" />
        <Input value={input} onChange={(e) => setInput(e.target.value)} placeholder="input / 1M" className="max-w-28" />
        <Input value={output} onChange={(e) => setOutput(e.target.value)} placeholder="output / 1M" className="max-w-28" />
        <Button
          onClick={async () => {
            if (!model) return toast.error("填写 model");
            try {
              await gatewayApi.createPricing({
                provider,
                model,
                inputPer1M: Number(input) || 0,
                outputPer1M: Number(output) || 0,
                cachedInputPer1M: 0,
                reasoningPer1M: 0,
                currency: "USD",
                effectiveFrom: "",
              });
              setModel("");
              reload();
              toast.success("已保存定价");
            } catch (e) {
              toast.error(e instanceof Error ? e.message : "保存失败");
            }
          }}
        >
          添加
        </Button>
      </div>
      <table className="w-full text-left text-[12px]">
        <thead className="text-[11px] text-muted-foreground">
          <tr>
            <th className="py-1">Provider</th>
            <th>Model</th>
            <th>In / 1M</th>
            <th>Out / 1M</th>
            <th>Cached</th>
            <th>Reasoning</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t border-border">
              <td className="py-1">{r.provider}</td>
              <td className="font-mono">{r.model}</td>
              <td className="font-mono">{r.inputPer1M}</td>
              <td className="font-mono">{r.outputPer1M}</td>
              <td className="font-mono">{r.cachedInputPer1M}</td>
              <td className="font-mono">{r.reasoningPer1M}</td>
              <td>
                <button
                  className="text-[11px] text-error"
                  onClick={async () => {
                    await gatewayApi.deletePricing(r.id);
                    reload();
                  }}
                >
                  删除
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

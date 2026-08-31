"use client";

import { useState } from "react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Progress } from "@/components/ui/progress";
import { useUi } from "@/lib/stores/ui";
import { useGateway } from "@/lib/stores/gateway";
import { AUTH_SCHEME_LABEL, PROVIDER_DESCRIPTORS, getDescriptor } from "@/descriptors/providers";
import { DynamicForm } from "./DynamicForm";
import { ProviderMark } from "@/components/common/ProviderMark";
import { CapabilityPills } from "@/components/common/CapabilityPills";
import { CredStatus, RequestStatus } from "@/components/common/StatusBadge";
import { formatCompact, formatDateTime, formatMs, formatPercent, formatUsd, quotaPct, relativeTime, remainingLabel } from "@/lib/format";
import { toast } from "sonner";
import { gatewayApi } from "@/lib/services/gateway";
import { setPlaygroundKey } from "@/lib/api/http";
import type { AuthScheme, VirtualCandidate } from "@/types";
import { Badge } from "@/components/ui/badge";

export function GlobalDialogs() {
  return (
    <>
      <AddProviderDialog />
      <AddCredentialDialog />
      <CredentialDrawer />
      <RequestDrawer />
      <CreateKeyDialog />
      <CreateVirtualDialog />
    </>
  );
}

function AddProviderDialog() {
  const open = useUi((s) => s.addProviderOpen);
  const close = useUi((s) => s.closeAddProvider);
  const add = useGateway((s) => s.addProvider);
  const [pick, setPick] = useState("openai");
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const d = getDescriptor(pick);

  return (
    <Dialog open={open} onOpenChange={(v) => !v && close()}>
      <DialogContent title="添加 Provider" description="接入官方支持的服务商，或自定义 OpenAI Compatible 上游。">
        <div className="grid gap-3">
          <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
            {PROVIDER_DESCRIPTORS.map((p) => (
              <button
                key={p.id}
                onClick={() => {
                  setPick(p.id);
                  setBaseUrl(p.defaultBaseUrl ?? "");
                  setName(p.name);
                }}
                className={`flex items-center gap-2 rounded-sm border px-2 py-1.5 text-left text-[12px] ${
                  pick === p.id ? "border-foreground/40 bg-accent" : "border-border hover:bg-accent/50"
                }`}
              >
                <ProviderMark mark={p.mark} color={p.color} size={20} />
                <span className="truncate">{p.name}</span>
              </button>
            ))}
          </div>
          <div className="grid gap-1">
            <Label>显示名称</Label>
            <Input value={name || d?.name || ""} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="grid gap-1">
            <Label>Base URL</Label>
            <Input value={baseUrl || d?.defaultBaseUrl || ""} onChange={(e) => setBaseUrl(e.target.value)} />
          </div>
          {d && <CapabilityPills items={d.capabilities} />}
          <p className="text-[11px] text-muted-foreground">
            仅接入用户有权使用并由 Provider 官方支持的认证方式。不支持 Cookie / 网页 Session / 浏览器窃取。
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={close}>
              取消
            </Button>
            <Button
              onClick={async () => {
                try {
                  await add({ descriptorId: pick, name: name || d?.name, baseUrl: baseUrl || d?.defaultBaseUrl });
                  toast.success("Provider 已添加");
                  close();
                } catch (e) {
                  toast.error(e instanceof Error ? e.message : "添加失败");
                }
              }}
            >
              添加
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function AddCredentialDialog() {
  const open = useUi((s) => s.addCredentialOpen);
  const preset = useUi((s) => s.addCredentialProviderId);
  const close = useUi((s) => s.closeAddCredential);
  const providers = useGateway((s) => s.providers);
  const add = useGateway((s) => s.addCredential);
  const [providerId, setProviderId] = useState(preset ?? providers[0]?.id ?? "openai");
  const [values, setValues] = useState<Record<string, string>>({});
  const [authType, setAuthType] = useState<AuthScheme>("api_key");

  const provider = providers.find((p) => p.id === (preset || providerId)) ?? providers.find((p) => p.id === providerId);
  const d = getDescriptor(provider?.descriptorId ?? providerId);

  const fields = d?.formFields ?? [];

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) close();
        else {
          const id = preset ?? providers[0]?.id ?? "openai";
          setProviderId(id);
          const desc = getDescriptor(providers.find((p) => p.id === id)?.descriptorId ?? id);
          setAuthType(desc?.authSchemes[0] ?? "api_key");
          setValues({ name: "", baseUrl: desc?.defaultBaseUrl ?? "" });
        }
      }}
    >
      <DialogContent title="添加凭据" description="Credential Pool · 动态表单由 Provider Descriptor 生成。" wide>
        <div className="grid gap-3">
          <div className="grid gap-1">
            <Label>Provider</Label>
            <Select value={preset || providerId} onValueChange={setProviderId} disabled={Boolean(preset)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {providers.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {d && (
            <div className="grid gap-1">
              <Label>认证类型</Label>
              <Select value={authType} onValueChange={(v) => setAuthType(v as AuthScheme)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {d.authSchemes.map((a) => (
                    <SelectItem key={a} value={a}>
                      {AUTH_SCHEME_LABEL[a]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          <DynamicForm
            fields={fields}
            values={values}
            onChange={(k, v) => setValues((s) => ({ ...s, [k]: v }))}
          />
          <p className="text-[11px] text-muted-foreground">
            仅接入用户有权使用并由 Provider 官方支持的认证方式。
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={close}>
              取消
            </Button>
            <Button
              onClick={async () => {
                if (!values.name) {
                  toast.error("请填写 Credential Name");
                  return;
                }
                try {
                  await add({
                    providerId: preset || providerId,
                    name: values.name,
                    authType,
                    extra: values,
                  });
                  toast.success("凭据已加入池中");
                  close();
                } catch (e) {
                  toast.error(e instanceof Error ? e.message : "保存失败");
                }
              }}
            >
              保存
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function CredentialDrawer() {
  const id = useUi((s) => s.credentialDrawerId);
  const close = useUi((s) => s.openCredential);
  const cred = useGateway((s) => s.credentials.find((c) => c.id === id));
  const provider = useGateway((s) => s.providers.find((p) => p.id === cred?.providerId));
  const models = useGateway((s) => s.models.filter((m) => m.providerId === cred?.providerId));
  const logs = useGateway((s) => s.logs.filter((l) => l.credentialId === id).slice(0, 8));
  const toggle = useGateway((s) => s.toggleCredential);
  const update = useGateway((s) => s.updateCredential);

  return (
    <Sheet open={Boolean(id)} onOpenChange={(v) => !v && close(undefined)}>
      <SheetContent title={cred?.name ?? "Credential"} description={provider?.name}>
        {cred && (
          <div className="space-y-4 text-[12px]">
            <div className="flex items-center justify-between">
              <CredStatus status={cred.status} />
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">启用</span>
                <Switch checked={cred.enabled} onCheckedChange={() => toggle(cred.id)} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <KV k="认证类型" v={AUTH_SCHEME_LABEL[cred.authType]} />
              <KV k="优先级" v={String(cred.priority)} />
              <KV k="权重" v={`${cred.weight}%`} />
              <KV k="Key" v={cred.maskedKey ?? "—"} />
              <KV k="今日请求" v={formatCompact(cred.requestsToday)} />
              <KV k="Token" v={formatCompact(cred.tokensToday)} />
              <KV k="延迟" v={formatMs(cred.avgLatencyMs)} />
              <KV k="成功率" v={formatPercent(cred.successRate)} />
              <KV k="最后使用" v={relativeTime(cred.lastUsed)} />
              <KV k="最后错误" v={cred.lastError ?? "—"} />
            </div>
            {cred.coolingUntil && (
              <div className="rounded-sm border border-border bg-muted/40 px-2 py-1.5 font-mono text-[11px]">
                Cooling {remainingLabel(cred.coolingUntil)} remaining
              </div>
            )}
            <div>
              <div className="mb-1 text-[11px] text-muted-foreground">额度</div>
              <QuotaLine label="RPM" used={cred.quota.rpmUsed} limit={cred.quota.rpmLimit} />
              <QuotaLine label="TPM" used={cred.quota.tpmUsed} limit={cred.quota.tpmLimit} />
              <QuotaLine label="Daily Token" used={cred.quota.dailyTokenUsed} limit={cred.quota.dailyTokenLimit} />
              <QuotaLine label="Monthly $" used={cred.quota.monthlySpend} limit={cred.quota.monthlyBudget} money />
            </div>
            <div>
              <div className="mb-1 text-[11px] text-muted-foreground">关联模型</div>
              <div className="flex flex-wrap gap-1">
                {models.slice(0, 8).map((m) => (
                  <Badge key={m.id}>{m.modelId}</Badge>
                ))}
              </div>
            </div>
            <div>
              <div className="mb-1 text-[11px] text-muted-foreground">错误历史</div>
              {cred.errorHistory.length === 0 ? (
                <div className="text-muted-foreground">无</div>
              ) : (
                cred.errorHistory.map((e, i) => (
                  <div key={i} className="font-mono text-[11px] text-error">
                    {formatDateTime(e.at)} · {e.code} · {e.message}
                  </div>
                ))
              )}
            </div>
            <div>
              <div className="mb-1 text-[11px] text-muted-foreground">近期日志</div>
              {logs.map((l) => (
                <div key={l.id} className="flex items-center justify-between py-0.5">
                  <span className="font-mono text-[11px] text-muted-foreground">{l.callId.slice(-8)}</span>
                  <RequestStatus status={l.status} />
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={async () => {
                  const r = await gatewayApi.testCredential(cred.id);
                  toast[r.ok ? "success" : "error"](r.message);
                }}
              >
                Test Connection
              </Button>
              <Button variant="outline" onClick={() => update(cred.id, { weight: Math.min(100, cred.weight + 5) })}>
                权重 +5
              </Button>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

function RequestDrawer() {
  const id = useUi((s) => s.requestDrawerId);
  const close = useUi((s) => s.openRequest);
  const log = useGateway((s) => s.logs.find((l) => l.id === id));
  const provider = useGateway((s) => s.providers.find((p) => p.id === log?.providerId));
  const cred = useGateway((s) => s.credentials.find((c) => c.id === log?.credentialId));
  const key = useGateway((s) => s.keys.find((k) => k.id === log?.clientKeyId));

  return (
    <Sheet open={Boolean(id)} onOpenChange={(v) => !v && close(undefined)}>
      <SheetContent title="Request Trace" description={log?.callId}>
        {log && (
          <div className="space-y-4 text-[12px]">
            <div className="flex items-center gap-2">
              <RequestStatus status={log.status} />
              <span className="text-muted-foreground">{formatDateTime(log.time)}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <KV k="Client" v={key?.name ?? "—"} />
              <KV k="Virtual" v={log.virtualModel} />
              <KV k="Real Model" v={log.realModel} />
              <KV k="Provider" v={provider?.name ?? log.providerId} />
              <KV k="Credential" v={cred?.name ?? log.credentialId} />
              <KV k="TTFT" v={formatMs(log.ttftMs)} />
              <KV k="Latency" v={formatMs(log.latencyMs)} />
              <KV k="In / Out" v={`${log.inputTokens} / ${log.outputTokens}`} />
              <KV k="Cached" v={String(log.cachedTokens)} />
              <KV k="Retries" v={String(log.retries)} />
              <KV k="Fallback" v={String(log.fallbackCount)} />
              <KV k="Cost" v={formatUsd(log.cost, 4)} />
            </div>
            <div>
              <div className="mb-2 text-[11px] text-muted-foreground">生命周期</div>
              <ol className="relative ml-2 border-l border-border">
                {log.trace.map((e, i) => (
                  <li key={i} className="mb-3 ml-3">
                    <span
                      className={`absolute -left-1 mt-1 size-2 rounded-full ${
                        e.kind === "ok"
                          ? "bg-success"
                          : e.kind === "error"
                            ? "bg-error"
                            : e.kind === "warn"
                              ? "bg-warning"
                              : "bg-muted-foreground"
                      }`}
                    />
                    <div className="font-mono text-[10px] text-muted-foreground">{e.at}</div>
                    <div>{e.label}</div>
                    {e.detail && <div className="text-[11px] text-muted-foreground">{e.detail}</div>}
                  </li>
                ))}
              </ol>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

function CreateKeyDialog() {
  const open = useUi((s) => s.createKeyOpen);
  const setOpen = useUi((s) => s.setCreateKeyOpen);
  const vms = useGateway((s) => s.virtualModels);
  const add = useGateway((s) => s.addKey);
  const [name, setName] = useState("");
  const [models, setModels] = useState<string[]>([]);
  const [created, setCreated] = useState<string>();

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v);
        if (!v) {
          setCreated(undefined);
          setName("");
        }
      }}
    >
      <DialogContent title="创建 Gateway API Key" description="这是客户端调用本 Gateway 的密钥，不是上游 Provider Key。">
        {created ? (
          <div className="space-y-3">
            <p className="text-[12px]">请立即复制，关闭后只显示脱敏值。</p>
            <code className="block rounded-sm border border-border bg-muted px-2 py-2 font-mono text-[12px]">{created}</code>
            <Button
              onClick={async () => {
                await navigator.clipboard.writeText(created);
                toast.success("已复制");
              }}
            >
              复制
            </Button>
          </div>
        ) : (
          <div className="grid gap-3">
            <div className="grid gap-1">
              <Label>Name</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="WorkBuddy" />
            </div>
            <div className="grid gap-1">
              <Label>Allowed Virtual Models</Label>
              <div className="flex flex-wrap gap-1">
                {vms.map((v) => {
                  const on = models.includes(v.slug);
                  return (
                    <button
                      key={v.id}
                      className={`rounded-sm border px-2 py-0.5 text-[11px] ${on ? "border-foreground/40 bg-accent" : "border-border"}`}
                      onClick={() => setModels((s) => (on ? s.filter((x) => x !== v.slug) : [...s, v.slug]))}
                    >
                      {v.slug}
                    </button>
                  );
                })}
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setOpen(false)}>
                取消
              </Button>
              <Button
                onClick={async () => {
                  if (!name) return toast.error("填写名称");
                  try {
                    const k = await add({
                      name,
                      allowedVirtualModels: models,
                      rpmLimit: 120,
                      tpmLimit: 400_000,
                      dailyTokenLimit: 10_000_000,
                      monthlyBudget: 40,
                      ipWhitelist: [],
                    });
                    setCreated(k.secret);
                    setPlaygroundKey(k.secret);
                    toast.success("API Key 已创建");
                  } catch (e) {
                    toast.error(e instanceof Error ? e.message : "创建失败");
                  }
                }}
              >
                创建
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function CreateVirtualDialog() {
  const open = useUi((s) => s.createVirtualOpen);
  const setOpen = useUi((s) => s.setCreateVirtualOpen);
  const models = useGateway((s) => s.models);
  const creds = useGateway((s) => s.credentials);
  const add = useGateway((s) => s.addVirtualModel);
  const [slug, setSlug] = useState("");
  const [desc, setDesc] = useState("");
  const [cands, setCands] = useState<VirtualCandidate[]>([]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent title="创建虚拟模型" description="客户端只调用 slug，Gateway 负责选真实模型。" wide>
        <div className="grid gap-3">
          <div className="grid grid-cols-2 gap-2">
            <div className="grid gap-1">
              <Label>Slug</Label>
              <Input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="coding" />
            </div>
            <div className="grid gap-1">
              <Label>说明</Label>
              <Input value={desc} onChange={(e) => setDesc(e.target.value)} />
            </div>
          </div>
          <div>
            <Label>添加候选</Label>
            <Select
              onValueChange={(id) => {
                const m = models.find((x) => x.id === id);
                if (!m) return;
                const cred = creds.find((c) => c.providerId === m.providerId);
                setCands((s) => [
                  ...s,
                  { modelId: m.id, credentialId: cred?.id, priority: s.length + 1, weight: 10 },
                ]);
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="选择真实模型" />
              </SelectTrigger>
              <SelectContent>
                {models.map((m) => (
                  <SelectItem key={m.id} value={m.id}>
                    {m.modelId}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="mt-2 space-y-1">
              {cands.map((c, i) => (
                <div key={i} className="flex items-center justify-between rounded-sm border border-border px-2 py-1">
                  <span className="font-mono text-[11px]">{models.find((m) => m.id === c.modelId)?.modelId}</span>
                  <span className="text-[11px] text-muted-foreground">P{c.priority}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>
              取消
            </Button>
            <Button
              onClick={async () => {
                if (!slug) return toast.error("填写 slug");
                try {
                  await add({
                    slug,
                    name: slug,
                    description: desc,
                    candidates: cands,
                    strategy: "failover",
                    fallbackChain: [],
                  });
                  toast.success("虚拟模型已创建");
                  setOpen(false);
                  setSlug("");
                  setCands([]);
                } catch (e) {
                  toast.error(e instanceof Error ? e.message : "创建失败");
                }
              }}
            >
              创建
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <div className="rounded-sm border border-border px-2 py-1.5">
      <div className="text-[10px] text-muted-foreground">{k}</div>
      <div className="truncate font-mono text-[11px]">{v}</div>
    </div>
  );
}

function QuotaLine({
  label,
  used,
  limit,
  money,
}: {
  label: string;
  used: number;
  limit: number;
  money?: boolean;
}) {
  const pct = quotaPct(used, limit);
  return (
    <div className="mb-2">
      <div className="mb-0.5 flex justify-between text-[11px]">
        <span>{label}</span>
        <span className="font-mono text-muted-foreground">
          {money ? formatUsd(used) : formatCompact(used)} / {money ? formatUsd(limit) : formatCompact(limit)} · {pct.toFixed(0)}%
        </span>
      </div>
      <Progress value={pct} />
    </div>
  );
}

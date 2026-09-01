"use client";

import { useEffect, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/PageHeader";
import { PageSkeleton } from "@/components/common/Skeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAsync } from "@/hooks/useAsync";
import { api } from "@/lib/api";
import { t } from "@/lib/i18n";
import type { SettingsState } from "@/types";

export function SettingsPage() {
  const { data, loading, error, reload } = useAsync(() => api.getSettings(), []);
  const [form, setForm] = useState<SettingsState | null>(null);
  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  if (loading || !form) return <PageSkeleton />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const save = async () => {
    await api.saveSettings(form);
    toast.success(t.settings.saved);
  };

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-5 md:p-6">
      <PageHeader
        title={t.settings.title}
        subtitle={t.settings.subtitle}
        actions={<Button onClick={save}>{t.common.save}</Button>}
      />
      <Tabs defaultValue="general">
        <TabsList className="flex h-auto flex-wrap">
          <TabsTrigger value="general">{t.settings.general}</TabsTrigger>
          <TabsTrigger value="gateway">{t.settings.gateway}</TabsTrigger>
          <TabsTrigger value="security">{t.settings.security}</TabsTrigger>
          <TabsTrigger value="billing">{t.settings.billing}</TabsTrigger>
          <TabsTrigger value="notification">{t.settings.notification}</TabsTrigger>
          <TabsTrigger value="database">{t.settings.database}</TabsTrigger>
          <TabsTrigger value="logs">{t.settings.logs}</TabsTrigger>
          <TabsTrigger value="advanced">{t.settings.advanced}</TabsTrigger>
        </TabsList>
        <TabsContent value="general" className="mt-3">
          <Panel>
            <Field label={t.settings.org} value={form.general.orgName} onChange={(v) => setForm({ ...form, general: { ...form.general, orgName: v } })} />
            <Field label={t.settings.timezone} value={form.general.timezone} onChange={(v) => setForm({ ...form, general: { ...form.general, timezone: v } })} />
            <Field label={t.settings.language} value={form.general.language} onChange={(v) => setForm({ ...form, general: { ...form.general, language: v } })} />
          </Panel>
        </TabsContent>
        <TabsContent value="gateway" className="mt-3">
          <Panel>
            <Field label={t.settings.baseUrl} value={form.gateway.baseUrl} onChange={(v) => setForm({ ...form, gateway: { ...form.gateway, baseUrl: v } })} />
            <Field label={t.settings.timeout} value={String(form.gateway.defaultTimeoutMs)} onChange={(v) => setForm({ ...form, gateway: { ...form.gateway, defaultTimeoutMs: Number(v) || 0 } })} />
            <Field label={t.settings.retry} value={String(form.gateway.retry)} onChange={(v) => setForm({ ...form, gateway: { ...form.gateway, retry: Number(v) || 0 } })} />
            <Toggle label={t.settings.stream} checked={form.gateway.streamEnabled} onChange={(v) => setForm({ ...form, gateway: { ...form.gateway, streamEnabled: v } })} />
          </Panel>
        </TabsContent>
        <TabsContent value="security" className="mt-3">
          <Panel>
            <Field label={t.settings.allowlist} value={form.security.ipAllowlist} onChange={(v) => setForm({ ...form, security: { ...form.security, ipAllowlist: v } })} />
            <Field label={t.settings.keyPrefix} value={form.security.keyPrefix} onChange={(v) => setForm({ ...form, security: { ...form.security, keyPrefix: v } })} />
            <Toggle label={t.settings.https} checked={form.security.requireHttps} onChange={(v) => setForm({ ...form, security: { ...form.security, requireHttps: v } })} />
          </Panel>
        </TabsContent>
        <TabsContent value="billing" className="mt-3">
          <Panel>
            <Field label={t.settings.currency} value={form.billing.currency} onChange={(v) => setForm({ ...form, billing: { ...form.billing, currency: v } })} />
            <Field label={t.settings.markup} value={String(form.billing.markup)} onChange={(v) => setForm({ ...form, billing: { ...form.billing, markup: Number(v) || 0 } })} />
          </Panel>
        </TabsContent>
        <TabsContent value="notification" className="mt-3">
          <Panel>
            <Field label={t.settings.email} value={form.notification.email} onChange={(v) => setForm({ ...form, notification: { ...form.notification, email: v } })} />
            <Field label={t.settings.webhook} value={form.notification.webhook} onChange={(v) => setForm({ ...form, notification: { ...form.notification, webhook: v } })} />
            <Toggle label={t.settings.onError} checked={form.notification.onError} onChange={(v) => setForm({ ...form, notification: { ...form.notification, onError: v } })} />
            <Toggle label={t.settings.onBudget} checked={form.notification.onBudget} onChange={(v) => setForm({ ...form, notification: { ...form.notification, onBudget: v } })} />
          </Panel>
        </TabsContent>
        <TabsContent value="database" className="mt-3">
          <Panel>
            <Field label={t.settings.driver} value={form.database.driver} onChange={(v) => setForm({ ...form, database: { ...form.database, driver: v } })} />
            <Field label={t.settings.host} value={form.database.host} onChange={(v) => setForm({ ...form, database: { ...form.database, host: v } })} />
          </Panel>
        </TabsContent>
        <TabsContent value="logs" className="mt-3">
          <Panel>
            <Field label={t.settings.retention} value={String(form.logs.retentionDays)} onChange={(v) => setForm({ ...form, logs: { ...form.logs, retentionDays: Number(v) || 0 } })} />
            <Field label={t.settings.sample} value={String(form.logs.sampleRate)} onChange={(v) => setForm({ ...form, logs: { ...form.logs, sampleRate: Number(v) || 0 } })} />
          </Panel>
        </TabsContent>
        <TabsContent value="advanced" className="mt-3">
          <Panel>
            <Toggle label={t.settings.debug} checked={form.advanced.debug} onChange={(v) => setForm({ ...form, advanced: { ...form.advanced, debug: v } })} />
            <Field label={t.settings.concurrency} value={String(form.advanced.maxConcurrency)} onChange={(v) => setForm({ ...form, advanced: { ...form.advanced, maxConcurrency: Number(v) || 0 } })} />
          </Panel>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Panel({ children }: { children: ReactNode }) {
  return <Card className="space-y-3 p-4">{children}</Card>;
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <Label>{label}</Label>
      <Switch checked={checked} onCheckedChange={onChange} />
    </div>
  );
}

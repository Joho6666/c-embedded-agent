"use client";

import { PageHeader } from "@/components/common/PageHeader";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { useGateway } from "@/lib/stores/gateway";
import { useTheme } from "next-themes";
import { toast } from "sonner";

export default function SettingsPage() {
  const settings = useGateway((s) => s.settings);
  const update = useGateway((s) => s.updateSettings);
  const { theme, setTheme } = useTheme();

  return (
    <div className="max-w-xl">
      <PageHeader title="系统设置" description="控制面配置。以后可直接接到真实 Gateway 配置 API。" />
      <div className="space-y-4 rounded-md border border-border bg-card p-4">
        <div className="grid gap-1">
          <Label>Gateway URL</Label>
          <Input value={settings.gatewayUrl} onChange={(e) => update({ gatewayUrl: e.target.value })} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="grid gap-1">
            <Label>Timeout (ms)</Label>
            <Input type="number" value={settings.timeoutMs} onChange={(e) => update({ timeoutMs: Number(e.target.value) })} />
          </div>
          <div className="grid gap-1">
            <Label>Retries</Label>
            <Input type="number" value={settings.retries} onChange={(e) => update({ retries: Number(e.target.value) })} />
          </div>
        </div>
        <div className="grid gap-1">
          <Label>日志保留（天）</Label>
          <Input
            type="number"
            value={settings.logRetentionDays}
            onChange={(e) => update({ logRetentionDays: Number(e.target.value) })}
          />
        </div>
        <label className="flex items-center justify-between text-[12px]">
          OAuth Credentials
          <Switch checked={settings.oauthCredentials} onCheckedChange={(v) => update({ oauthCredentials: v })} />
        </label>
        <label className="flex items-center justify-between text-[12px]">
          USD Budget
          <Switch checked={settings.usdBudget} onCheckedChange={(v) => update({ usdBudget: v })} />
        </label>
        <label className="flex items-center justify-between text-[12px]">
          Dark Mode
          <Switch checked={theme !== "light"} onCheckedChange={(v) => setTheme(v ? "dark" : "light")} />
        </label>
        <p className="text-[11px] text-muted-foreground">
          仅接入用户有权使用并由 Provider 官方支持的认证方式。不支持 Cookie / 网页 Session / 浏览器窃取。
        </p>
        <Button onClick={() => toast.success("设置已保存（本地 mock）")}>保存</Button>
      </div>
    </div>
  );
}

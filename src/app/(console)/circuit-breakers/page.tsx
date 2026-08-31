"use client";

import Link from "next/link";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { useGateway } from "@/lib/stores/gateway";
import { formatDateTime, remainingLabel } from "@/lib/format";
import { toast } from "sonner";
import { gatewayApi } from "@/lib/services/gateway";
import { Empty } from "@/components/common/Empty";

export default function CircuitPage() {
  const circuits = useGateway((s) => s.circuits);
  const creds = useGateway((s) => s.credentials);
  const providers = useGateway((s) => s.providers);
  const recover = useGateway((s) => s.recoverCircuit);
  const toggle = useGateway((s) => s.toggleCredential);

  return (
    <div>
      <PageHeader title="熔断中心" description="Circuit Open 凭据。可恢复、禁用、测试或跳转日志。" />
      {circuits.length === 0 ? (
        <Empty title="当前没有打开的熔断" hint="连续失败 / 5xx / 连接失败会进入此列表。" />
      ) : (
        <div className="overflow-auto rounded-md border border-border">
          <table className="w-full min-w-[960px] text-left text-[12px]">
            <thead className="bg-muted/40 text-[11px] text-muted-foreground">
              <tr>
                {["Credential", "Provider", "Reason", "Last Error", "Failures", "Opened", "Recover", "Cooldown", ""].map((h) => (
                  <th key={h} className="px-2 py-2 font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {circuits.map((cb) => {
                const c = creds.find((x) => x.id === cb.credentialId);
                const p = providers.find((x) => x.id === cb.providerId);
                return (
                  <tr key={cb.id} className="border-t border-border">
                    <td className="px-2 py-2">{c?.name}</td>
                    <td>{p?.name}</td>
                    <td>{cb.reason}</td>
                    <td className="max-w-48 truncate font-mono text-[11px]">{cb.lastError}</td>
                    <td className="font-mono">{cb.failureCount}</td>
                    <td className="text-[11px]">{formatDateTime(cb.openedAt)}</td>
                    <td className="text-[11px]">{formatDateTime(cb.recoverAt)}</td>
                    <td className="font-mono text-sky-400">{remainingLabel(cb.recoverAt)}</td>
                    <td className="space-x-1 whitespace-nowrap px-2">
                      <Button
                        size="sm"
                        onClick={() => {
                          recover(cb.id);
                          toast.success("已恢复，状态回到 Healthy");
                        }}
                      >
                        Recover
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => c && toggle(c.id)}>
                        Disable
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={async () => {
                          if (!c) return;
                          const r = await gatewayApi.testCredential(c.id);
                          toast[r.ok ? "success" : "error"](r.message);
                        }}
                      >
                        Test
                      </Button>
                      <Button size="sm" variant="ghost" asChild>
                        <Link href="/requests">Logs</Link>
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

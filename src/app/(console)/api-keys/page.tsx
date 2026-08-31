"use client";

import { useState } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useGateway } from "@/lib/stores/gateway";
import { useUi } from "@/lib/stores/ui";
import { formatCompact, formatUsd, maskKey, relativeTime } from "@/lib/format";
import { toast } from "sonner";
import { copyText } from "@/lib/format";

export default function ApiKeysPage() {
  const keys = useGateway((s) => s.keys);
  const rotate = useGateway((s) => s.rotateKey);
  const toggle = useGateway((s) => s.toggleKey);
  const del = useGateway((s) => s.deleteKey);
  const open = useUi((s) => s.setCreateKeyOpen);
  const [show, setShow] = useState<Record<string, boolean>>({});

  return (
    <div>
      <PageHeader
        title="API Keys"
        description="谁可以调用我的 Gateway。不是上游 Provider 密钥。"
        actions={<Button onClick={() => open(true)}>Create</Button>}
      />
      <div className="overflow-auto rounded-md border border-border">
        <table className="w-full min-w-[1080px] text-left text-[12px]">
          <thead className="bg-muted/40 text-[11px] text-muted-foreground">
            <tr>
              {["Name", "Key", "Status", "Models", "RPM", "TPM", "Daily", "Budget", "Last Used", "Usage", ""].map((h) => (
                <th key={h} className="px-2 py-2 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {keys.map((k) => (
              <tr key={k.id} className="border-t border-border">
                <td className="px-2 py-2">{k.name}</td>
                <td className="font-mono text-[11px]">
                  {show[k.id] ? k.secret : maskKey(k.secret)}
                  <button className="ml-2 text-muted-foreground hover:text-foreground" onClick={() => setShow((s) => ({ ...s, [k.id]: !s[k.id] }))}>
                    {show[k.id] ? "Hide" : "Show"}
                  </button>
                </td>
                <td>
                  <Badge tone={k.status === "active" ? "success" : k.status === "expired" ? "error" : "neutral"}>{k.status}</Badge>
                </td>
                <td className="max-w-40 truncate">{k.allowedVirtualModels.join(", ")}</td>
                <td className="font-mono">{k.rpmLimit}</td>
                <td className="font-mono">{formatCompact(k.tpmLimit)}</td>
                <td className="font-mono">{formatCompact(k.dailyTokenLimit)}</td>
                <td className="font-mono">{formatUsd(k.monthlyBudget, 0)}</td>
                <td>{relativeTime(k.lastUsed)}</td>
                <td className="font-mono">
                  {formatCompact(k.requestsToday)} / {formatUsd(k.costToday)}
                </td>
                <td className="space-x-1 whitespace-nowrap px-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={async () => {
                      await copyText(k.secret);
                      toast.success("已复制");
                    }}
                  >
                    Copy
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      const n = rotate(k.id);
                      toast.success(`已轮换 ${n.prefix}…`);
                    }}
                  >
                    Rotate
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => toggle(k.id)}>
                    {k.status === "active" ? "Disable" : "Enable"}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => del(k.id)}>
                    Delete
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

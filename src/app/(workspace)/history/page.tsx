"use client";

import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Empty } from "@/components/common/Empty";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";
import { useLive } from "@/lib/stores/live-store";
import { API_BASE } from "@/lib/api/client";

interface RunRow {
  id: string;
  prompt?: string;
  status?: string;
  project_id?: string;
  started_at?: string;
}

export default function HistoryPage() {
  const mode = useLive((s) => s.mode);
  const [rows, setRows] = useState<RunRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== "live") {
      setRows([]);
      setErr("LIVE 时显示真实 runs。DEMO 不回放假历史。");
      return;
    }
    void fetch(`${API_BASE}/api/runs`)
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status} /api/runs`);
        return r.json();
      })
      .then((d: RunRow[]) => {
        setRows(Array.isArray(d) ? d : []);
        setErr(null);
      })
      .catch((e: Error) => {
        setRows([]);
        setErr(e.message || "Backend capability unavailable");
      });
  }, [mode]);

  return (
    <div className="p-5">
      <h1 className="text-[18px] font-semibold">历史记录</h1>
      {err && <div className="mt-3"><CapabilityBanner reason={err} /></div>}
      {rows && rows.length === 0 && !err ? <div className="mt-4"><Empty title="无记录" /></div> : null}
      {rows && rows.length > 0 && (
        <div className="mt-4 divide-y divide-border rounded-sm border border-border bg-panel">
          {rows.map((t) => (
            <div key={t.id} className="flex items-center justify-between px-3 py-3">
              <div>
                <div className="font-mono text-[12px]">{t.id}</div>
                <div className="text-[13px]">{t.prompt || "(no prompt)"}</div>
                <div className="text-[11px] text-muted-foreground">{t.project_id} · {t.started_at || ""}</div>
              </div>
              <StatusBadge status={t.status || "idle"} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

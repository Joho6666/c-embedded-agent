"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { StatusBadge } from "@/components/common/StatusBadge";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";
import { useLive } from "@/lib/stores/live-store";
import { API_BASE } from "@/lib/api/client";

interface RunEvent {
  id?: string;
  type: string;
  status?: string;
  title?: string;
  detail?: string | null;
  logs?: string | null;
  reason?: string | null;
  data?: unknown;
  [k: string]: unknown;
}

interface RunDetail {
  id: string;
  status?: string;
  prompt?: string;
  events?: RunEvent[];
}

interface ArtifactAnalysis {
  available?: boolean;
  status?: string;
  sections?: { name: string; bytes: number }[];
  largestSymbols?: { name: string; bytes: number; type: string }[];
  budgets?: { flash: { used: number; max: number; status: string }; ram: { used: number; max: number; status: string } };
  reason?: string;
}

const TYPE_ORDER = ["plan", "approval", "llm", "tool", "file_diff", "compile", "terminal", "flash", "reset", "serial", "validation", "diagnostic", "test", "fault"];

export default function RunInspectorPage() {
  const params = useParams<{ runId: string }>();
  const runId = params?.runId;
  const mode = useLive((s) => s.mode);
  const [run, setRun] = useState<RunDetail | null>(null);
  const [analysis, setAnalysis] = useState<ArtifactAnalysis | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!runId || mode !== "live") {
      setErr("LIVE 时显示真实 run 证据。DEMO 不回放假数据。");
      return;
    }
    void fetch(`${API_BASE}/api/runs/${runId}`)
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status} /api/runs/${runId}`);
        return r.json() as Promise<RunDetail>;
      })
      .then((d) => {
        setRun(d);
        setErr(null);
        const projectId = (d as unknown as { project_id?: string }).project_id;
        if (projectId) {
          void fetch(`${API_BASE}/api/projects/${projectId}/artifacts/analysis`)
            .then((r) => (r.ok ? r.json() : null))
            .then((a) => setAnalysis(a))
            .catch(() => setAnalysis(null));
        }
      })
      .catch((e: Error) => setErr(e.message));
  }, [runId, mode]);

  const events = run?.events || [];
  const ordered = [...events].sort(
    (a, b) => TYPE_ORDER.indexOf(a.type) - TYPE_ORDER.indexOf(b.type)
  );
  const repaired = events.some((e) => e.type === "compile" && e.status === "failed") && events.some((e) => e.type === "compile" && e.status === "success");

  return (
    <div className="p-5">
      <div className="flex items-center justify-between">
        <h1 className="text-[18px] font-semibold">Run Inspector{runId ? ` · ${runId}` : ""}</h1>
        {run?.status && <StatusBadge status={run.status} />}
      </div>
      {err && <div className="mt-3"><CapabilityBanner reason={err} /></div>}
      {run?.prompt && <p className="mt-2 text-[13px]">{run.prompt}</p>}
      {repaired && (
        <div className="mt-2 text-[12px] text-muted-foreground">检测到修复循环：先失败后编译成功。</div>
      )}

      {ordered.length > 0 && (
        <section className="mt-4">
          <h2 className="text-[13px] font-medium">执行轨迹（Plan → LLM → 工具 → 编译 → 硬件）</h2>
          <div className="mt-2 divide-y divide-border rounded-sm border border-border bg-panel">
            {ordered.map((e, i) => (
              <div key={e.id || i} className="px-3 py-2.5">
                <div className="flex items-center justify-between">
                  <div className="font-mono text-[11px] text-muted-foreground">
                    [{e.type}]
                    {e.title ? ` ${e.title}` : ""}
                  </div>
                  {e.status ? <StatusBadge status={e.status} /> : null}
                </div>
                {e.detail ? <div className="mt-1 text-[12px]">{e.detail}</div> : null}
                {e.logs ? (
                  <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded-sm bg-black/40 p-2 text-[11px]">{e.logs}</pre>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      )}

      {analysis?.available && analysis.budgets && (
        <section className="mt-5">
          <h2 className="text-[13px] font-medium">固件尺寸 / 预算门</h2>
          <div className="mt-2 grid gap-2 md:grid-cols-2">
            <div className="rounded-sm border border-border bg-panel p-3 text-[12px]">
              <div>
                Flash: {analysis.budgets.flash.used} / {analysis.budgets.flash.max} bytes · {analysis.budgets.flash.status}
              </div>
              <div className="mt-1">
                RAM: {analysis.budgets.ram.used} / {analysis.budgets.ram.max} bytes · {analysis.budgets.ram.status}
              </div>
            </div>
            <div className="rounded-sm border border-border bg-panel p-3 text-[12px]">
              <div className="font-medium">最大符号</div>
              {analysis.largestSymbols?.slice(0, 6).map((s) => (
                <div key={s.name} className="mt-1 flex justify-between font-mono text-[11px]">
                  <span>{s.name}</span>
                  <span>{s.bytes} B</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

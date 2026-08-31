"use client";

import { testSuite } from "@/lib/mock/build";
import { StatusBadge } from "@/components/common/StatusBadge";
import { cn } from "@/lib/utils";

export default function TestingPage() {
  return (
    <div className="p-5">
      <h1 className="text-[18px] font-semibold">测试</h1>
      <p className="text-[12px] text-muted-foreground">Unity / Ceedling · {testSuite.name}</p>
      <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4">
        <Stat k="Passed" v={testSuite.passed} cls="text-success" />
        <Stat k="Failed" v={testSuite.failed} cls="text-error" />
        <Stat k="Skipped" v={testSuite.skipped} />
        <Stat k="Coverage" v={`${testSuite.coverage}%`} />
      </div>
      <div className="mt-4 overflow-hidden rounded-sm border border-border">
        {testSuite.cases.map((c) => (
          <div key={c.name} className="flex items-center justify-between border-b border-border px-3 py-2 last:border-0">
            <div>
              <div className="font-mono text-[12px]">{c.name}</div>
              {c.message && <div className="text-[11px] text-error">{c.message}</div>}
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-[11px] text-muted-foreground">{c.durationMs}ms</span>
              <StatusBadge
                status={c.status === "pass" ? "success" : c.status === "fail" ? "failed" : "pending"}
                label={c.status}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Stat({ k, v, cls }: { k: string; v: number | string; cls?: string }) {
  return (
    <div className="rounded-sm border border-border bg-panel p-3">
      <div className="text-[11px] text-muted-foreground">{k}</div>
      <div className={cn("mt-1 font-mono text-[20px]", cls)}>{v}</div>
    </div>
  );
}

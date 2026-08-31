"use client";

import { testSuite } from "@/lib/mock/build";
import { StatusBadge } from "@/components/common/StatusBadge";

export default function TestingPage() {
  return (
    <div className="p-5">
      <h1 className="text-[18px] font-semibold">测试</h1>
      <div className="mt-4 grid grid-cols-4 gap-2">
        <div className="rounded-sm border border-border bg-panel p-3">
          <div className="text-[11px] text-muted-foreground">通过</div>
          <div className="font-mono text-[20px] text-success">{testSuite.passed}</div>
        </div>
        <div className="rounded-sm border border-border bg-panel p-3">
          <div className="text-[11px] text-muted-foreground">失败</div>
          <div className="font-mono text-[20px] text-error">{testSuite.failed}</div>
        </div>
        <div className="rounded-sm border border-border bg-panel p-3">
          <div className="text-[11px] text-muted-foreground">覆盖率</div>
          <div className="font-mono text-[20px]">{testSuite.coverage}%</div>
        </div>
      </div>
      <div className="mt-4 rounded-sm border border-border">
        {testSuite.cases.map((c) => (
          <div key={c.name} className="flex items-center justify-between border-b border-border px-3 py-2 last:border-0">
            <span className="font-mono text-[12px]">{c.name}</span>
            <StatusBadge status={c.status === "pass" ? "success" : c.status === "fail" ? "failed" : "pending"} label={c.status} />
          </div>
        ))}
      </div>
    </div>
  );
}

"use client";

import { ProblemList } from "@/components/problems/ProblemList";
import { problems } from "@/lib/mock/build";

export default function ProblemsPage() {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-5 py-3">
        <h1 className="text-[18px] font-semibold">Problems</h1>
        <p className="text-[12px] text-muted-foreground">类似 VS Code 的诊断列表，可交给 Agent 修复</p>
      </div>
      <div className="min-h-0 flex-1">
        <ProblemList items={problems} />
      </div>
    </div>
  );
}

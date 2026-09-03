"use client";

import { ProblemList } from "@/components/problems/ProblemList";

export default function ProblemsPage() {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-5 py-3">
        <h1 className="text-[18px] font-semibold">问题</h1>
        <p className="text-[12px] text-muted-foreground">编译与静态分析诊断，可交给 Agent 修复</p>
      </div>
      <div className="min-h-0 flex-1">
        <ProblemList />
      </div>
    </div>
  );
}

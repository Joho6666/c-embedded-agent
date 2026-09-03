"use client";

import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useAgent } from "@/lib/stores/agent-store";
import { riskLabel } from "@/lib/i18n";

export function ApprovalCard() {
  const approval = useAgent((s) => s.approval);
  const approve = useAgent((s) => s.approve);
  if (!approval) return null;
  return (
    <div className="m-3 rounded-md border border-warning/50 bg-warning/10 p-3">
      <div className="text-[11px] font-medium text-warning">需要确认 · 风险 {riskLabel[approval.risk] ?? approval.risk}</div>
      <h3 className="mt-1 text-[13px] font-medium">{approval.title}</h3>
      <p className="mt-1 text-[12px] text-muted-foreground">{approval.summary}</p>
      <ol className="mt-2 list-decimal pl-4 text-[12px]">
        {approval.steps.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ol>
      <div className="mt-3 flex flex-wrap gap-1">
        <Button
          size="sm"
          onClick={() => {
            void approve("approved");
            toast.success("已批准");
          }}
        >
          批准
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            void approve("once");
            toast.success("批准一次");
          }}
        >
          批准一次
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => {
            void approve("always");
            toast.success("本会话始终允许烧录");
          }}
        >
          始终允许
        </Button>
        <Button
          size="sm"
          variant="destructive"
          onClick={() => {
            void approve("rejected");
            toast.message("已拒绝");
          }}
        >
          拒绝
        </Button>
      </div>
    </div>
  );
}

"use client";

import { AgentPlan } from "@/components/agent/AgentPlan";
import { AgentTimeline } from "@/components/agent/AgentTimeline";
import { AgentSuggestedFix } from "@/components/agent/AgentSuggestedFix";
import { ArtifactList } from "@/components/agent/ArtifactList";
import { ApprovalCard } from "@/components/agent/ApprovalCard";
import { HardwareContextPanel } from "@/components/agent/HardwareContextPanel";
import { TaskInput } from "@/components/agent/TaskInput";
import { SerialMonitor } from "@/components/hardware/SerialMonitor";
import { useAgent } from "@/lib/stores/agent-store";
import { useWorkspaceUI, type AgentPanelTab } from "@/lib/stores/workspace-store";
import { goldenPlan } from "@/lib/mock/golden-path";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const TABS: Array<{ id: AgentPanelTab; label: string }> = [
  { id: "conversation", label: "会话" },
  { id: "plan", label: "执行计划" },
  { id: "hardware", label: "硬件上下文" },
  { id: "knowledge", label: "知识库" },
];

export function ContextPanel() {
  const tab = useWorkspaceUI((s) => s.agentPanelTab);
  const setTab = useWorkspaceUI((s) => s.setAgentPanelTab);
  const events = useAgent((s) => s.events);
  const plan = useAgent((s) => s.activeRun?.plan) ?? goldenPlan;
  const setKnowledgeId = useWorkspaceUI((s) => s.setKnowledgeId);

  return (
    <div className="flex h-full min-w-0 flex-col border-l border-border bg-panel">
      <div className="flex h-8 shrink-0 items-center border-b border-border px-2 text-[12px] font-medium">C-Agent 智能助手</div>
      <div className="flex h-8 shrink-0 items-center gap-1 border-b border-border px-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={cn(
              "h-8 px-2 text-[11px]",
              tab === t.id ? "border-b-2 border-primary text-foreground" : "text-muted-foreground",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {tab === "conversation" && (
          <div className="p-2">
            <AgentTimeline events={events} />
            <ApprovalCard />
          </div>
        )}
        {tab === "plan" && (
          <>
            <AgentPlan plan={plan} />
            <AgentSuggestedFix />
            <ArtifactList />
          </>
        )}
        {tab === "hardware" && <HardwareContextPanel />}
        {tab === "knowledge" && (
          <div className="p-3 text-[12px] text-muted-foreground">
            <p>知识库检索走 LIVE `/api/knowledge`。DEMO 不伪造命中。</p>
            <Button size="sm" className="mt-2" variant="outline" onClick={() => setKnowledgeId("rm0008")}>
              打开知识库
            </Button>
          </div>
        )}
      </div>
      <div className="shrink-0 border-t border-border">
        <div className="h-36 border-b border-border">
          <SerialMonitor compact />
        </div>
        <TaskInput />
      </div>
    </div>
  );
}

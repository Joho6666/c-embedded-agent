"use client";

import { Group, Panel, Separator } from "react-resizable-panels";
import { AgentTimeline } from "@/components/agent/AgentTimeline";
import { TaskInput } from "@/components/agent/TaskInput";
import { PlanViewer } from "@/components/agent/PlanViewer";
import { HardwareContextPanel } from "@/components/agent/HardwareContextPanel";
import { ApprovalCard } from "@/components/agent/ApprovalCard";
import { ArtifactList } from "@/components/agent/ArtifactList";
import { FileTree } from "@/components/editor/FileTree";
import { CodeEditor } from "@/components/editor/CodeEditor";
import { Button } from "@/components/ui/button";
import { useAgent } from "@/lib/stores/agent-store";
import { useEditor } from "@/lib/stores/editor-store";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";
import { goldenPlan } from "@/lib/mock/golden-path";

export default function AgentPage() {
  const events = useAgent((s) => s.events);
  const prompt = useAgent((s) => s.prompt);
  const runPlan = useAgent((s) => s.activeRun?.plan);
  const plan = runPlan ?? goldenPlan;
  const start = useAgent((s) => s.startGoldenPath);
  const view = useWorkspaceUI((s) => s.agentView);
  const setView = useWorkspaceUI((s) => s.setAgentView);
  const openFile = useEditor((s) => s.openFile);
  const activeFile = useEditor((s) => s.activeFile);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border bg-panel px-3 py-2">
        <div className="min-w-0">
          <div className="text-[11px] text-muted-foreground">当前任务</div>
          <div className="truncate text-[13px] font-medium">{prompt}</div>
        </div>
        <div className="flex shrink-0 gap-1">
          <Button size="sm" variant={view === "timeline" ? "default" : "outline"} onClick={() => setView("timeline")}>
            时间线
          </Button>
          <Button size="sm" variant={view === "code" ? "default" : "outline"} onClick={() => setView("code")}>
            代码
          </Button>
          <Button size="sm" variant="outline" onClick={() => void start()}>
            STM32 LED 演示
          </Button>
        </div>
      </div>
      <Group orientation="horizontal" className="min-h-0 flex-1">
        <Panel defaultSize="18" minSize="12" maxSize="28">
          <div className="h-full border-r border-border bg-panel">
            <div className="border-b border-border px-2 py-1.5 text-[11px] text-muted-foreground">文件</div>
            <FileTree
              active={activeFile}
              onSelect={(p) => {
                openFile(p);
                setView("code");
              }}
            />
          </div>
        </Panel>
        <Separator className="w-px bg-border" />
        <Panel defaultSize="54" minSize="36">
          <div className="flex h-full flex-col">
            <div className="min-h-0 flex-1 overflow-auto">
              {view === "code" ? (
                <CodeEditor />
              ) : (
                <div className="p-3">
                  <AgentTimeline events={events} />
                </div>
              )}
            </div>
            <TaskInput />
          </div>
        </Panel>
        <Separator className="w-px bg-border" />
        <Panel defaultSize="28" minSize="18">
          <div className="h-full overflow-auto">
            <HardwareContextPanel />
            <ApprovalCard />
            <PlanViewer plan={plan} />
            <ArtifactList />
          </div>
        </Panel>
      </Group>
    </div>
  );
}

"use client";

import { Group, Panel, Separator } from "react-resizable-panels";
import { Explorer } from "@/components/workbench/Explorer";
import { ContextPanel } from "@/components/workbench/ContextPanel";
import { CodeEditor } from "@/components/editor/CodeEditor";
import { AgentTimeline } from "@/components/agent/AgentTimeline";
import { HardwareTimeline } from "@/components/hardware/HardwareTimeline";
import { HardwareRunButton } from "@/components/hardware/HardwareRunButton";
import { ProblemList } from "@/components/problems/ProblemList";
import { useAgent } from "@/lib/stores/agent-store";
import { useHardware } from "@/lib/stores/hardware-store";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";

export default function WorkspacePage() {
  const activity = useWorkspaceUI((s) => s.activity);
  const events = useAgent((s) => s.events);
  const hw = useHardware((s) => s.hardwareRun);

  return (
    <Group orientation="horizontal" className="h-full">
      <Panel defaultSize="18" minSize="12" maxSize="28">
        {activity === "search" ? (
          <div className="p-3 text-[12px] text-muted-foreground">工程内搜索尚未接入索引。请用资源管理器打开文件。</div>
        ) : activity === "build" ? (
          <div className="p-3 text-[12px] text-muted-foreground">构建输出在底部 TERMINAL / OUTPUT。使用工具栏「构建」。</div>
        ) : activity === "problems" ? (
          <ProblemList />
        ) : activity === "hardware" ? (
          <div className="overflow-auto p-3">
            <HardwareRunButton />
            <div className="mt-2">
              <HardwareTimeline result={hw} />
            </div>
          </div>
        ) : activity === "agent" ? (
          <div className="h-full overflow-auto p-2">
            <AgentTimeline events={events} />
          </div>
        ) : (
          <Explorer />
        )}
      </Panel>
      <Separator className="w-px bg-border" />
      <Panel defaultSize="54" minSize="36">
        <div className="flex h-full flex-col">
          {activity === "debug" && (
            <div className="border-b border-border p-2">
              <CapabilityBanner reason="GDB Debug Session: Not Available / Experimental" />
            </div>
          )}
          <div className="min-h-0 flex-1">
            <CodeEditor />
          </div>
        </div>
      </Panel>
      <Separator className="w-px bg-border" />
      <Panel defaultSize="28" minSize="18" maxSize="40">
        <ContextPanel />
      </Panel>
    </Group>
  );
}

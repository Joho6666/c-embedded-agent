"use client";

import { Group, Panel, Separator } from "react-resizable-panels";
import { CodeEditor } from "@/components/editor/CodeEditor";
import { FileTree } from "@/components/editor/FileTree";
import { useEditor } from "@/lib/stores/editor-store";

export default function CodePage() {
  const activeFile = useEditor((s) => s.activeFile);
  const openFile = useEditor((s) => s.openFile);
  return (
    <Group orientation="horizontal" className="h-full">
      <Panel defaultSize="22" minSize="14">
        <div className="h-full border-r border-border bg-panel">
          <div className="border-b border-border px-3 py-1.5 text-[11px] text-muted-foreground">资源管理器</div>
          <FileTree active={activeFile} onSelect={openFile} />
        </div>
      </Panel>
      <Separator className="w-px bg-border" />
      <Panel defaultSize="78">
        <CodeEditor />
      </Panel>
    </Group>
  );
}

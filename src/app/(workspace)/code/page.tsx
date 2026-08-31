"use client";

import { Group, Panel, Separator } from "react-resizable-panels";
import { CodeEditor } from "@/components/editor/CodeEditor";
import { FileTree } from "@/components/editor/FileTree";
import { fileTree } from "@/lib/mock/files";
import { useWorkspace } from "@/lib/stores/workspace";

export default function CodePage() {
  const files = useWorkspace((s) => s.files);
  const activeFile = useWorkspace((s) => s.activeFile);
  const setActiveFile = useWorkspace((s) => s.setActiveFile);
  const diffs = useWorkspace((s) => s.diffs);
  const acceptDiff = useWorkspace((s) => s.acceptDiff);
  const rejectDiff = useWorkspace((s) => s.rejectDiff);
  const acceptAll = useWorkspace((s) => s.acceptAll);
  const file = files[activeFile];
  const diff = diffs.find((d) => d.path === activeFile);

  return (
    <Group orientation="horizontal" className="h-full">
      <Panel defaultSize="22" minSize="14" maxSize="36">
        <div className="h-full border-r border-border bg-panel">
          <div className="border-b border-border px-3 py-1.5 text-[11px] text-muted-foreground">资源管理器</div>
          <FileTree tree={fileTree} active={activeFile} onSelect={setActiveFile} />
        </div>
      </Panel>
      <Separator className="w-px bg-border" />
      <Panel defaultSize="78" minSize="40">
        <CodeEditor
          path={activeFile}
          language={file?.language ?? "c"}
          value={file?.content ?? ""}
          diff={diff}
          onAccept={() => acceptDiff(activeFile)}
          onReject={() => rejectDiff(activeFile)}
          onAcceptAll={acceptAll}
        />
      </Panel>
    </Group>
  );
}

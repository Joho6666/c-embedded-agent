"use client";

import { FileTree } from "@/components/editor/FileTree";
import { useEditor } from "@/lib/stores/editor-store";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";
import { useProject, currentProject } from "@/lib/stores/project-store";

export function Explorer() {
  const active = useEditor((s) => s.activeFile);
  const openFile = useEditor((s) => s.openFile);
  const setView = useWorkspaceUI((s) => s.setAgentView);
  const project = currentProject();
  const id = useProject((s) => s.projectId);

  return (
    <div className="flex h-full flex-col bg-panel">
      <div className="border-b border-border px-2 py-1.5 text-[11px] text-muted-foreground">资源管理器</div>
      <div className="px-2 py-1 font-mono text-[11px] text-muted-foreground">{project.name || id}</div>
      <div className="min-h-0 flex-1 overflow-auto">
        <FileTree
          active={active}
          onSelect={(p) => {
            openFile(p);
            setView("code");
          }}
        />
      </div>
    </div>
  );
}

"use client";

import dynamic from "next/dynamic";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useEditor } from "@/lib/stores/editor-store";
import { useAgent } from "@/lib/stores/agent-store";
import { cn } from "@/lib/utils";

const Monaco = dynamic(() => import("@monaco-editor/react"), { ssr: false });
const DiffEditor = dynamic(() => import("@monaco-editor/react").then((m) => m.DiffEditor), { ssr: false });

export function CodeEditor() {
  const files = useEditor((s) => s.files);
  const activeFile = useEditor((s) => s.activeFile);
  const revealLine = useEditor((s) => s.revealLine);
  const tabs = useEditor((s) => s.tabs);
  const patches = useEditor((s) => s.patches);
  const openFile = useEditor((s) => s.openFile);
  const closeTab = useEditor((s) => s.closeTab);
  const setContent = useEditor((s) => s.setContent);
  const saveFile = useEditor((s) => s.saveFile);
  const acceptPatch = useEditor((s) => s.acceptPatch);
  const rejectPatch = useEditor((s) => s.rejectPatch);
  const acceptAll = useEditor((s) => s.acceptAll);
  const undoLastAiChange = useEditor((s) => s.undoLastAiChange);
  const approve = useAgent((s) => s.approve);

  const gate = async (kind: "accept" | "reject" | "all") => {
    const pendingAll = patches.filter((p) => p.status === "pending");
    const target = kind === "all" ? pendingAll : pending ? [pending] : [];
    if (kind === "accept" && pending) acceptPatch(pending.id);
    if (kind === "reject" && pending) rejectPatch(pending.id);
    if (kind === "all") acceptAll();
    for (const p of target) {
      if (p.approvalId) await approve(kind === "reject" ? "rejected" : "approved", p.approvalId);
    }
    toast.success(kind === "reject" ? "已拒绝修改" : "已应用到工程");
  };

  const file = files[activeFile];
  const pending = patches.find((p) => p.path === activeFile && p.status === "pending");
  const dirty = file ? file.content !== file.saved : false;

  return (
    <div className="flex h-full flex-col bg-panel">
      <div className="flex h-8 items-center gap-1 overflow-x-auto border-b border-border px-1">
        {tabs.map((t) => {
          const f = files[t];
          const isDirty = f && f.content !== f.saved;
          return (
            <button
              key={t}
              onClick={() => openFile(t)}
              className={cn(
                "flex items-center gap-1 rounded-sm px-2 py-1 font-mono text-[11px]",
                t === activeFile ? "bg-accent" : "text-muted-foreground",
              )}
            >
              {t.split("/").pop()}
              {isDirty ? " ●" : ""}
              <span
                className="ml-1 text-muted-foreground"
                onClick={(e) => {
                  e.stopPropagation();
                  if (isDirty && !window.confirm(`「${t.split("/").pop()}」尚未保存，确定关闭？`)) return;
                  closeTab(t);
                }}
              >
                ×
              </span>
            </button>
          );
        })}
        <div className="ml-auto flex gap-1 pr-1">
          {dirty && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                saveFile();
                toast.success("已保存");
              }}
            >
              保存
            </Button>
          )}
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              undoLastAiChange();
              toast.message("已撤销上次 AI 修改");
            }}
          >
            撤销 AI 修改
          </Button>
        </div>
      </div>
      {pending && (
        <div className="flex items-center justify-between border-b border-border bg-panel-2 px-3 py-1 text-[11px]">
          <span>AI 差异 · {pending.reason} · 尚未应用到工程</span>
          <div className="flex gap-1">
            <Button size="sm" variant="success" onClick={() => void gate("accept")}>
              接受
            </Button>
            <Button size="sm" variant="outline" onClick={() => void gate("reject")}>
              拒绝
            </Button>
            <Button size="sm" onClick={() => void gate("all")}>
              全部接受
            </Button>
          </div>
        </div>
      )}
      <div className="min-h-0 flex-1">
        {!file && tabs.length === 0 ? (
          <div className="flex h-full items-center justify-center text-[13px] text-muted-foreground">没有打开的文件</div>
        ) : pending ? (
          <DiffEditor
            theme="vs-dark"
            language={file?.language === "makefile" ? "plaintext" : file?.language ?? "c"}
            original={pending.original}
            modified={pending.proposed}
            options={{ readOnly: true, renderSideBySide: true, minimap: { enabled: false }, fontSize: 12 }}
          />
        ) : (
          <Monaco
            theme="vs-dark"
            language={file?.language === "makefile" ? "plaintext" : file?.language ?? "c"}
            value={file?.content ?? ""}
            onChange={(v) => setContent(activeFile, v ?? "")}
            onMount={(editor) => {
              if (revealLine && revealLine > 0) {
                editor.revealLineInCenter(revealLine);
                editor.setPosition({ lineNumber: revealLine, column: 1 });
                editor.focus();
              }
            }}
            options={{
              readOnly: false,
              minimap: { enabled: false },
              fontSize: 12,
              automaticLayout: true,
              fontFamily: "Geist Mono, JetBrains Mono, ui-monospace, Menlo, Consolas, monospace",
            }}
          />
        )}
      </div>
    </div>
  );
}

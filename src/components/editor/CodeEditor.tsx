"use client";

import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";
import type { CodeDiff } from "@/types/debug";

const Monaco = dynamic(() => import("@monaco-editor/react"), { ssr: false });

export function CodeEditor({
  path,
  language,
  value,
  diff,
  onAccept,
  onReject,
  onAcceptAll,
}: {
  path: string;
  language: string;
  value: string;
  diff?: CodeDiff;
  onAccept?: () => void;
  onReject?: () => void;
  onAcceptAll?: () => void;
}) {
  const showDiff = diff && diff.accepted == null;
  return (
    <div className="flex h-full flex-col bg-panel">
      <div className="flex h-8 items-center justify-between border-b border-border px-3 text-[12px]">
        <span className="font-mono">{path}</span>
        {showDiff && (
          <div className="flex gap-1">
            <Button size="sm" variant="success" onClick={onAccept}>
              Accept
            </Button>
            <Button size="sm" variant="outline" onClick={onReject}>
              Reject
            </Button>
            <Button size="sm" onClick={onAcceptAll}>
              Accept All
            </Button>
          </div>
        )}
        {diff?.accepted === true && <span className="text-success">已接受修改</span>}
        {diff?.accepted === false && <span className="text-muted-foreground">已拒绝修改</span>}
      </div>
      {showDiff && (
        <div className="border-b border-border bg-panel-2 px-3 py-1 text-[11px] text-muted-foreground">
          AI Diff · 绿色新增 · 红色删除
        </div>
      )}
      <div className="min-h-0 flex-1">
        {showDiff ? (
          <div className="grid h-full grid-cols-2">
            <div className="overflow-auto border-r border-border bg-[#1a1010] p-3 font-mono text-[12px] leading-5 text-red-300 whitespace-pre">
              {diff.original}
            </div>
            <div className="overflow-auto bg-[#0f1a12] p-3 font-mono text-[12px] leading-5 text-emerald-300 whitespace-pre">
              {diff.modified}
            </div>
          </div>
        ) : (
          <Monaco
            theme="vs-dark"
            language={language === "makefile" ? "plaintext" : language}
            value={value}
            options={{
              minimap: { enabled: false },
              fontSize: 12,
              fontFamily: "Geist Mono, JetBrains Mono, ui-monospace, Menlo, Consolas, monospace",
              lineNumbers: "on",
              scrollBeyondLastLine: false,
              automaticLayout: true,
              readOnly: true,
              padding: { top: 8 },
            }}
          />
        )}
      </div>
    </div>
  );
}

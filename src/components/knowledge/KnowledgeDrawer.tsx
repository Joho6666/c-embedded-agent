"use client";

import { knowledgeDocs } from "@/lib/mock/knowledge";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";

export function KnowledgeDrawer() {
  const id = useWorkspaceUI((s) => s.knowledgeId);
  const setId = useWorkspaceUI((s) => s.setKnowledgeId);
  const doc = knowledgeDocs.find((d) => d.id === id);
  if (!doc) return null;
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/40" onClick={() => setId(undefined)}>
      <aside
        className="h-full w-[min(420px,100%)] overflow-auto border-l border-border bg-panel p-4 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="text-[11px] text-muted-foreground">{doc.sourceType}</div>
            <h2 className="text-[16px] font-semibold">{doc.title}</h2>
            {doc.subtitle && <div className="font-mono text-[12px] text-info">{doc.subtitle}</div>}
          </div>
          <button className="text-[12px] text-muted-foreground hover:text-foreground" onClick={() => setId(undefined)}>
            关闭
          </button>
        </div>
        <dl className="mt-4 space-y-1 text-[12px]">
          <div>厂商 {doc.vendor}</div>
          <div>版本 {doc.version}</div>
          {doc.pages != null && <div>页数 {doc.pages}</div>}
          <div>片段 {doc.chunks}</div>
          <div>索引 {doc.indexed ? "已完成" : "未完成"}</div>
        </dl>
        <p className="mt-4 text-[12px] leading-6 text-muted-foreground">
          {doc.id === "rm0008"
            ? "第 9.2 节 GPIO · PA5 属于 GPIOA。配置为推挽输出前需使能 RCC GPIOA 时钟。Agent 检索分数 0.94。"
            : "文档摘要为 Mock。后续由知识库 embedding 填充章节摘录。"}
        </p>
      </aside>
    </div>
  );
}

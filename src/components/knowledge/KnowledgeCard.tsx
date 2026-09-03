import type { KnowledgeDocument } from "@/types/knowledge";
import { StatusBadge } from "@/components/common/StatusBadge";

export function KnowledgeCard({ doc, onOpen }: { doc: KnowledgeDocument; onOpen?: () => void }) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="w-full rounded-md border border-border bg-panel p-3.5 text-left transition-colors hover:border-zinc-600 hover:bg-accent/20"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-[13px] font-medium">{doc.title}</h3>
          {doc.subtitle && <div className="font-mono text-[11px] text-muted-foreground">{doc.subtitle}</div>}
        </div>
        <div className="flex flex-col items-end gap-1">
          <StatusBadge status={doc.indexed ? "success" : "pending"} label={doc.indexed ? "✓ 已索引" : "待索引"} />
          <span className="rounded-sm border border-border px-1 text-[10px] uppercase text-muted-foreground">
            {doc.origin ?? "official"}
          </span>
        </div>
      </div>
      <dl className="mt-2 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
        <div>来源 {doc.source}</div>
        <div>版本 {doc.version}</div>
        <div>{doc.sourceType}</div>
        <div>{doc.pages ? `${doc.pages} 页` : `${doc.chunks} 片段`}</div>
      </dl>
    </button>
  );
}

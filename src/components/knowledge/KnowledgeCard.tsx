import type { KnowledgeDoc } from "@/types/knowledge";
import { StatusBadge } from "@/components/common/StatusBadge";

export function KnowledgeCard({ doc }: { doc: KnowledgeDoc }) {
  return (
    <article className="rounded-sm border border-border bg-panel p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-[13px] font-medium">{doc.title}</h3>
          {doc.subtitle && <div className="font-mono text-[11px] text-muted-foreground">{doc.subtitle}</div>}
        </div>
        <StatusBadge status={doc.indexed ? "success" : "pending"} label={doc.indexed ? "✓ Indexed" : "Pending"} />
      </div>
      <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
        <div>来源 {doc.source}</div>
        <div>版本 {doc.version}</div>
        <div>更新 {doc.updatedAt}</div>
        <div>
          {doc.format}
          {doc.pages ? ` · ${doc.pages} pages` : ` · ${doc.docCount} docs`}
        </div>
      </dl>
    </article>
  );
}

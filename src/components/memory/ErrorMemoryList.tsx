import Link from "next/link";
import type { ErrorMemoryEntry } from "@/types/memory";

function rate(v: number | null) {
  if (v == null) return "Not Tested";
  return `${Math.round(v * 100)}%`;
}

export function ErrorMemoryList({ items }: { items: ErrorMemoryEntry[] }) {
  return (
    <div className="divide-y divide-border overflow-hidden rounded-md border border-border bg-panel">
      {items.map((e) => (
        <Link key={e.id} href={`/memory/errors/${e.id}`} className="flex items-center justify-between px-3 py-2.5 hover:bg-accent/40">
          <div className="min-w-0">
            <div className="truncate font-mono text-[13px]">{e.pattern}</div>
            <div className="text-[11px] text-muted-foreground">
              {e.tag} · {e.mcu} · {e.occurrences} hits
            </div>
          </div>
          <div className="shrink-0 font-mono text-[12px] text-muted-foreground">{rate(e.successRate)}</div>
        </Link>
      ))}
    </div>
  );
}

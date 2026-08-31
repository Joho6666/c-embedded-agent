export function Empty({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-card/40 px-4 py-14 text-center">
      <div className="mx-auto mb-3 size-10 rounded-md border border-border bg-panel-2" />
      <div className="text-[13px] font-medium">{title}</div>
      {hint && <div className="mx-auto mt-1 max-w-sm text-[12px] text-muted-foreground">{hint}</div>}
    </div>
  );
}

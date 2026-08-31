export function Metric({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="relative overflow-hidden rounded-lg border border-border bg-card px-3.5 py-3">
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-[linear-gradient(to_top,color-mix(in_srgb,var(--foreground)_4%,transparent),transparent)]" />
      <div className="text-[11px] text-muted-foreground">{label}</div>
      <div className="mt-1.5 font-mono text-[22px] leading-none tracking-tight">{value}</div>
      {hint && <div className="mt-1.5 text-[10px] text-muted-foreground">{hint}</div>}
    </div>
  );
}

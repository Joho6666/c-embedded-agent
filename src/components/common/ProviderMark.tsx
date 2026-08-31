export function ProviderMark({
  mark,
  color,
  size = 28,
}: {
  mark: string;
  color: string;
  size?: number;
}) {
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-sm font-mono text-[10px] font-semibold text-white"
      style={{ width: size, height: size, background: color }}
    >
      {mark}
    </span>
  );
}

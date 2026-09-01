export function CapabilityBanner({
  reason,
  kind = "unavailable",
}: {
  reason?: string;
  kind?: "unavailable" | "not-tested" | "empty";
}) {
  const text =
    reason ||
    (kind === "not-tested"
      ? "Not Tested"
      : kind === "empty"
        ? "No data"
        : "Backend capability unavailable");
  return (
    <div className="rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-[12px] text-warning">
      {text}
    </div>
  );
}

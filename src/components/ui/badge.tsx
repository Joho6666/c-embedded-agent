import { cn } from "@/lib/utils";

export function Badge({
  className,
  tone = "neutral",
  ...props
}: React.ComponentProps<"span"> & {
  tone?: "neutral" | "success" | "warning" | "error" | "info" | "limit" | "cool";
}) {
  const tones = {
    neutral: "bg-muted text-muted-foreground",
    success: "bg-success/15 text-success",
    warning: "bg-warning/15 text-warning",
    error: "bg-error/15 text-error",
    info: "bg-info/15 text-info",
    limit: "bg-orange-500/15 text-orange-400",
    cool: "bg-sky-500/15 text-sky-400",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm px-1.5 py-0.5 text-[10px] font-medium tracking-wide",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}

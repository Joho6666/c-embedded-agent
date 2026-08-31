import { cn } from "@/lib/utils";

const map = {
  ready: { label: "就绪", cls: "text-muted-foreground bg-muted" },
  working: { label: "工作中", cls: "text-info bg-info/10" },
  success: { label: "成功", cls: "text-success bg-success/10" },
  passed: { label: "通过", cls: "text-success bg-success/10" },
  warning: { label: "警告", cls: "text-warning bg-warning/10" },
  error: { label: "错误", cls: "text-error bg-error/10" },
  failed: { label: "失败", cls: "text-error bg-error/10" },
  pending: { label: "待处理", cls: "text-muted-foreground bg-muted" },
  running: { label: "进行中", cls: "text-info bg-info/10" },
  connected: { label: "已连接", cls: "text-success bg-success/10" },
  disconnected: { label: "未连接", cls: "text-muted-foreground bg-muted" },
  idle: { label: "空闲", cls: "text-muted-foreground bg-muted" },
  complete: { label: "完成", cls: "text-success bg-success/10" },
  stopped: { label: "已停止", cls: "text-warning bg-warning/10" },
  pass: { label: "通过", cls: "text-success bg-success/10" },
  fail: { label: "失败", cls: "text-error bg-error/10" },
  skip: { label: "跳过", cls: "text-muted-foreground bg-muted" },
} as const;

export function StatusBadge({
  status,
  label,
  className,
}: {
  status: string;
  label?: string;
  className?: string;
}) {
  const item = map[status as keyof typeof map];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm px-1.5 py-0.5 text-[10px] font-medium tracking-wide",
        item?.cls ?? "bg-muted text-muted-foreground",
        className,
      )}
    >
      {label ?? item?.label ?? status}
    </span>
  );
}

export function Dot({ tone = "success" }: { tone?: "success" | "warning" | "error" | "neutral" | "info" }) {
  const colors = {
    success: "bg-success",
    warning: "bg-warning",
    error: "bg-error",
    neutral: "bg-muted-foreground",
    info: "bg-info",
  };
  return <span className={`inline-block size-1.5 rounded-full ${colors[tone]}`} />;
}

"use client";

import { useRouter } from "next/navigation";
import { AlertTriangle, Bot, Bug, Cpu, Files, Hammer, Search, Settings } from "lucide-react";
import { useWorkspaceUI, type ActivityId } from "@/lib/stores/workspace-store";
import { cn } from "@/lib/utils";

const ITEMS: Array<{ id: ActivityId; label: string; icon: typeof Files; href?: string }> = [
  { id: "explorer", label: "资源管理器", icon: Files },
  { id: "agent", label: "智能助手", icon: Bot },
  { id: "search", label: "搜索", icon: Search },
  { id: "build", label: "构建", icon: Hammer },
  { id: "debug", label: "调试", icon: Bug, href: "/debug" },
  { id: "hardware", label: "硬件", icon: Cpu },
  { id: "problems", label: "问题", icon: AlertTriangle },
];

export function ActivityBar() {
  const activity = useWorkspaceUI((s) => s.activity);
  const setActivity = useWorkspaceUI((s) => s.setActivity);
  const setBottomTab = useWorkspaceUI((s) => s.setBottomTab);
  const router = useRouter();

  return (
    <aside className="hidden h-full w-12 shrink-0 flex-col border-r border-border bg-chrome md:flex">
      <nav className="flex flex-1 flex-col items-center gap-1 py-2">
        {ITEMS.map((item) => {
          const Icon = item.icon;
          const active = activity === item.id;
          return (
            <button
              key={item.id}
              type="button"
              title={item.label}
              onClick={() => {
                setActivity(item.id);
                if (item.id === "build") setBottomTab("terminal");
                if (item.id === "problems") setBottomTab("problems");
                if (item.id === "debug" && item.href) router.push(item.href);
              }}
              className={cn(
                "relative flex size-10 flex-col items-center justify-center rounded-sm text-muted-foreground hover:text-foreground",
                active && "bg-accent text-foreground",
              )}
            >
              {active && <span className="absolute left-0 top-1.5 bottom-1.5 w-[2px] rounded-full bg-primary" />}
              <Icon className="size-4" />
              <span className="mt-0.5 text-[8px] leading-none">{item.label.slice(0, 4)}</span>
            </button>
          );
        })}
      </nav>
      <button
        type="button"
        title="设置"
        onClick={() => router.push("/settings")}
        className="mb-2 flex size-10 items-center justify-center self-center text-muted-foreground hover:text-foreground"
      >
        <Settings className="size-4" />
      </button>
    </aside>
  );
}

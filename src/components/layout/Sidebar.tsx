"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Moon, PanelLeft, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { navItems } from "./nav";
import { useUi } from "@/lib/stores/ui";
import { useGateway } from "@/lib/stores/gateway";
import { cn } from "@/lib/utils";
import { Dot } from "@/components/common/StatusBadge";

export function Sidebar() {
  const pathname = usePathname();
  const collapsed = useUi((s) => s.sidebarCollapsed);
  const toggle = useUi((s) => s.toggleSidebar);
  const health = useGateway((s) => s.health.overall);
  const { theme, setTheme } = useTheme();

  const groups = Array.from(new Set(navItems.map((i) => i.group)));

  return (
    <aside
      className={cn(
        "hidden h-full shrink-0 flex-col border-r border-border bg-chrome md:flex",
        collapsed ? "w-[52px]" : "w-[196px]",
      )}
    >
      <div className={cn("flex h-12 items-center gap-2 border-b border-border px-3", collapsed && "justify-center px-0")}>
        <span className="flex size-6 items-center justify-center rounded-sm bg-foreground font-mono text-[10px] text-background">
          GW
        </span>
        {!collapsed && (
          <div className="min-w-0 leading-tight">
            <div className="truncate text-[12px] font-medium">AI Gateway</div>
            <div className="truncate text-[10px] text-muted-foreground">Control Plane</div>
          </div>
        )}
      </div>
      <button
        onClick={toggle}
        className="flex h-8 items-center gap-2 px-3 text-muted-foreground hover:text-foreground"
        title="折叠侧栏"
      >
        <PanelLeft className="size-3.5" />
        {!collapsed && <span className="text-[11px]">导航</span>}
      </button>
      <nav className="flex-1 overflow-auto px-1 pb-2">
        {groups.map((g) => (
          <div key={g} className="mb-2">
            {!collapsed && (
              <div className="px-2 pt-2 pb-1 text-[10px] tracking-wide text-muted-foreground uppercase">{g}</div>
            )}
            {navItems
              .filter((i) => i.group === g)
              .map((item) => {
                const active =
                  item.href === "/" ? pathname === "/" : pathname === item.href || pathname.startsWith(`${item.href}/`);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    title={item.label}
                    className={cn(
                      "flex items-center gap-2 rounded-sm px-2 py-1.5 text-[12px]",
                      active
                        ? "bg-accent text-foreground"
                        : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                      collapsed && "justify-center px-0",
                    )}
                  >
                    <Icon className="size-3.5 shrink-0" />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </Link>
                );
              })}
          </div>
        ))}
      </nav>
      <div className={cn("border-t border-border p-2 text-[10px] text-muted-foreground", collapsed && "px-1")}>
        <div className={cn("flex items-center gap-1.5 px-1 py-1", collapsed && "justify-center")}>
          <Dot tone={health === "operational" ? "success" : "warning"} />
          {!collapsed && <span className="capitalize">{health}</span>}
        </div>
        {!collapsed && <div className="px-1">v0.1.0</div>}
        <button
          className={cn("mt-1 flex w-full items-center gap-2 rounded-sm px-1 py-1 hover:bg-accent", collapsed && "justify-center")}
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          {theme === "dark" ? <Sun className="size-3.5" /> : <Moon className="size-3.5" />}
          {!collapsed && <span>主题</span>}
        </button>
        {!collapsed && <div className="mt-1 px-1">operator</div>}
      </div>
    </aside>
  );
}

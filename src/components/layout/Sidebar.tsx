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
        collapsed ? "w-[56px]" : "w-[220px]",
      )}
    >
      <div className={cn("flex h-12 items-center gap-2.5 border-b border-border px-3", collapsed && "justify-center px-0")}>
        <span className="flex size-7 items-center justify-center rounded-[6px] bg-foreground font-mono text-[10px] font-semibold text-background">
          GW
        </span>
        {!collapsed && (
          <div className="min-w-0 leading-tight">
            <div className="truncate text-[13px] font-medium tracking-tight">AI Gateway</div>
            <div className="truncate text-[10px] text-muted-foreground">Control Plane</div>
          </div>
        )}
      </div>
      <button
        onClick={toggle}
        className="mx-2 mt-2 flex h-8 items-center gap-2 rounded-md px-2 text-muted-foreground hover:bg-accent hover:text-foreground"
        title="折叠侧栏"
      >
        <PanelLeft className="size-3.5" />
        {!collapsed && <span className="text-[11px]">折叠</span>}
      </button>
      <nav className="flex-1 overflow-auto px-2 pb-2">
        {groups.map((g) => (
          <div key={g} className="mb-3">
            {!collapsed && (
              <div className="px-2 pt-3 pb-1 text-[10px] font-medium tracking-[0.14em] text-muted-foreground uppercase">
                {g}
              </div>
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
                      "relative flex items-center gap-2.5 rounded-md px-2 py-[7px] text-[12.5px] transition-colors",
                      active
                        ? "bg-accent text-foreground"
                        : "text-muted-foreground hover:bg-accent/70 hover:text-foreground",
                      collapsed && "justify-center px-0",
                    )}
                  >
                    {active && <span className="absolute top-1.5 bottom-1.5 left-0 w-[2px] rounded-full bg-foreground" />}
                    <Icon className="size-3.5 shrink-0" />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </Link>
                );
              })}
          </div>
        ))}
      </nav>
      <div className={cn("border-t border-border p-2 text-[11px] text-muted-foreground", collapsed && "px-1")}>
        <div
          className={cn(
            "flex items-center gap-2 rounded-md border border-border bg-panel-2 px-2 py-1.5",
            collapsed && "justify-center border-0 bg-transparent px-0",
          )}
        >
          <Dot tone={health === "operational" ? "success" : "warning"} />
          {!collapsed && <span className="capitalize">{health}</span>}
          {!collapsed && <span className="ml-auto font-mono text-[10px] opacity-70">v0.1.0</span>}
        </div>
        <button
          className={cn(
            "mt-1.5 flex w-full items-center gap-2 rounded-md px-2 py-1.5 hover:bg-accent hover:text-foreground",
            collapsed && "justify-center",
          )}
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          {theme === "dark" ? <Sun className="size-3.5" /> : <Moon className="size-3.5" />}
          {!collapsed && <span>主题</span>}
        </button>
      </div>
    </aside>
  );
}

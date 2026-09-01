"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PanelLeft } from "lucide-react";
import { navItems } from "./nav";
import { useUi } from "@/lib/ui-store";
import { cn } from "@/lib/utils";
import { t } from "@/lib/i18n";

export function Sidebar() {
  const pathname = usePathname();
  const collapsed = useUi((s) => s.sidebarCollapsed);
  const toggle = useUi((s) => s.toggleSidebar);

  return (
    <aside
      className={cn(
        "hidden h-full shrink-0 flex-col border-r border-border bg-chrome md:flex",
        collapsed ? "w-[52px]" : "w-[220px]",
      )}
    >
      <div className={cn("flex h-12 items-center gap-2 border-b border-border px-3", collapsed && "justify-center px-0")}>
        <span className="flex size-6 items-center justify-center rounded-sm border border-border bg-foreground text-[10px] font-semibold text-background">
          UG
        </span>
        {!collapsed && (
          <div className="min-w-0">
            <div className="truncate text-[13px] font-semibold tracking-tight">{t.brand}</div>
            <div className="truncate text-[10px] text-muted-foreground">{t.tagline}</div>
          </div>
        )}
      </div>
      <button
        onClick={toggle}
        className="flex h-9 items-center gap-2 px-3 text-muted-foreground hover:text-foreground"
        aria-label="toggle-sidebar"
      >
        <PanelLeft className="size-3.5" />
        {!collapsed && <span className="text-[11px]">{t.common.nav}</span>}
      </button>
      <nav className="flex flex-1 flex-col gap-0.5 p-1.5">
        {navItems.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              title={item.label}
              className={cn(
                "relative flex items-center gap-2 rounded-sm px-2 py-1.5 text-[12px]",
                active ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/70 hover:text-foreground",
                collapsed && "justify-center px-0",
              )}
            >
              {active && <span className="absolute top-1.5 bottom-1.5 left-0 w-[2px] rounded-full bg-foreground" />}
              <Icon className="size-3.5 shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

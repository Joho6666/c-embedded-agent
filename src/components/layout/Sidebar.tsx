"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PanelLeft } from "lucide-react";
import { moreNavItems, navItems } from "./nav";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const pathname = usePathname();
  const collapsed = useWorkspaceUI((s) => s.sidebarCollapsed);
  const toggle = useWorkspaceUI((s) => s.toggleSidebar);

  return (
    <aside
      className={cn(
        "hidden h-full shrink-0 flex-col border-r border-border bg-chrome md:flex",
        collapsed ? "w-12" : "w-[188px]",
      )}
    >
      <button
        onClick={toggle}
        className="flex h-10 items-center gap-2 px-3 text-muted-foreground hover:text-foreground"
      >
        <PanelLeft className="size-3.5" />
        {!collapsed && <span className="text-[11px]">导航</span>}
      </button>
      <nav className="flex flex-1 flex-col gap-0.5 p-1.5">
        {navItems.map((item) => {
          const active =
            item.href === "/" ? pathname === "/" : pathname === item.href || pathname.startsWith(`${item.href}/`);
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
              {active && <span className="absolute left-0 top-1.5 bottom-1.5 w-[2px] rounded-full bg-primary" />}
              <Icon className="size-3.5 shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>
      {!collapsed && (
        <div className="border-t border-border p-1.5">
          <div className="px-2 py-1 text-[10px] text-muted-foreground">Engineering Tools</div>
          {moreNavItems.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center rounded-sm px-2 py-1 text-[11px]",
                  active ? "text-foreground" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      )}
    </aside>
  );
}

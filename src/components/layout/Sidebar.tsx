"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PanelLeft } from "lucide-react";
import { navItems } from "./nav";
import { useWorkspace } from "@/lib/stores/workspace";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const pathname = usePathname();
  const collapsed = useWorkspace((s) => s.sidebarCollapsed);
  const toggle = useWorkspace((s) => s.toggleSidebar);

  return (
    <aside
      className={cn(
        "hidden h-full shrink-0 flex-col border-r border-border bg-chrome md:flex",
        collapsed ? "w-12" : "w-[176px]",
      )}
    >
      <button
        onClick={toggle}
        className="flex h-8 items-center gap-2 px-3 text-muted-foreground hover:text-foreground"
        title="折叠侧栏"
      >
        <PanelLeft className="size-3.5" />
        {!collapsed && <span className="text-[11px]">导航</span>}
      </button>
      <nav className="flex flex-1 flex-col gap-0.5 p-1">
        {navItems.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname === item.href || pathname.startsWith(`${item.href}/`);
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
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

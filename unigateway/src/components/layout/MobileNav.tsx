"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { navItems } from "./nav";
import { useUi } from "@/lib/ui-store";
import { cn } from "@/lib/utils";

export function MobileNav() {
  const pathname = usePathname();
  const open = useUi((s) => s.mobileNav);
  const setOpen = useUi((s) => s.setMobileNav);
  const mobile = navItems.filter((i) => i.mobile);

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-40 bg-black/40 md:hidden" onClick={() => setOpen(false)}>
          <div className="h-full w-[220px] bg-chrome p-2" onClick={(e) => e.stopPropagation()}>
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className={cn(
                    "flex items-center gap-2 rounded-sm px-2 py-2 text-[12px]",
                    active ? "bg-accent" : "text-muted-foreground",
                  )}
                >
                  <Icon className="size-3.5" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      )}
      <nav className="flex h-12 items-center justify-around border-t border-border bg-chrome md:hidden">
        {mobile.map((item) => {
          const Icon = item.icon;
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link key={item.href} href={item.href} className={cn("flex flex-col items-center gap-0.5 text-[10px]", active ? "text-foreground" : "text-muted-foreground")}>
              <Icon className="size-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </>
  );
}

"use client";

import { Menu, Moon, Search, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { useUi } from "@/lib/ui-store";
import { t } from "@/lib/i18n";

export function TopBar() {
  const setCommand = useUi((s) => s.setCommandOpen);
  const setMobile = useUi((s) => s.setMobileNav);
  const { theme, setTheme } = useTheme();

  return (
    <header className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-border bg-chrome px-3">
      <div className="flex min-w-0 items-center gap-2">
        <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setMobile(true)}>
          <Menu />
        </Button>
        <button
          onClick={() => setCommand(true)}
          className="flex h-8 w-[min(420px,52vw)] items-center gap-2 rounded-sm border border-border bg-panel-2 px-2 text-left text-[12px] text-muted-foreground hover:border-foreground/20"
        >
          <Search className="size-3.5" />
          <span className="truncate">{t.search}</span>
          <kbd className="ml-auto hidden rounded border border-border px-1 font-mono text-[10px] sm:inline">⌘K</kbd>
        </button>
      </div>
      <div className="flex items-center gap-1.5">
        <Button variant="ghost" size="icon" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
          {theme === "light" ? <Moon /> : <Sun />}
        </Button>
        <div className="hidden items-center gap-2 rounded-sm border border-border px-2 py-1 sm:flex">
          <span className="size-1.5 rounded-full bg-success" />
          <span className="font-mono text-[11px] text-muted-foreground">api.unigateway.dev</span>
        </div>
      </div>
    </header>
  );
}

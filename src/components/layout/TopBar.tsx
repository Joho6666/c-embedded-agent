"use client";

import { Copy, Menu, Plus, Search, TerminalSquare } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useGateway } from "@/lib/stores/gateway";
import { useUi } from "@/lib/stores/ui";
import { copyText } from "@/lib/format";
import { toast } from "sonner";
import { Dot } from "@/components/common/StatusBadge";
import { navItems } from "./nav";
import { useState } from "react";

export function TopBar() {
  const url = useGateway((s) => s.settings.gatewayUrl);
  const health = useGateway((s) => s.health.overall);
  const openCmd = useUi((s) => s.setCommandOpen);
  const openProv = useUi((s) => s.openAddProvider);
  const openCred = useUi((s) => s.openAddCredential);
  const [mobileNav, setMobileNav] = useState(false);

  return (
    <>
    <header className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-border bg-chrome px-4">
      <div className="flex min-w-0 items-center gap-3">
        <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setMobileNav((v) => !v)}>
          <Menu className="size-3.5" />
        </Button>
        <div className="hidden leading-tight sm:block">
          <div className="text-[13px] font-medium">Universal AI Gateway</div>
          <div className="text-[11px] text-muted-foreground">One API. Every Model.</div>
        </div>
        <span className="hidden items-center gap-1.5 rounded-sm border border-border px-1.5 py-0.5 text-[11px] md:inline-flex">
          <Dot tone={health === "operational" ? "success" : "warning"} />
          <span className="capitalize">{health}</span>
        </span>
        <button
          className="hidden max-w-[280px] truncate rounded-sm border border-border bg-panel-2 px-2 py-1 font-mono text-[11px] text-muted-foreground hover:text-foreground lg:block"
          onClick={async () => {
            await copyText(url);
            toast.success("已复制");
          }}
          title={url}
        >
          {url}
        </button>
      </div>
      <div className="flex items-center gap-1.5">
        <Button variant="ghost" size="icon" onClick={() => openCmd(true)} title="Command">
          <Search className="size-3.5" />
        </Button>
        <Button variant="outline" onClick={() => openProv()}>
          <Plus className="size-3.5" />
          Provider
        </Button>
        <Button variant="outline" onClick={() => openCred()}>
          <Plus className="size-3.5" />
          凭据
        </Button>
        <Button asChild>
          <Link href="/playground">
            <TerminalSquare className="size-3.5" />
            Playground
          </Link>
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={async () => {
            await copyText(url);
            toast.success("已复制 Gateway URL");
          }}
        >
          <Copy className="size-3.5" />
        </Button>
      </div>
    </header>
    {mobileNav && (
      <div className="border-b border-border bg-chrome p-2 md:hidden">
        <div className="grid grid-cols-2 gap-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-sm px-2 py-1.5 text-[12px] text-muted-foreground hover:bg-accent hover:text-foreground"
              onClick={() => setMobileNav(false)}
            >
              {item.label}
            </Link>
          ))}
        </div>
      </div>
    )}
    </>
  );
}

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import { useTheme } from "next-themes";
import { navItems } from "./nav";
import { useUi } from "@/lib/ui-store";
import { t } from "@/lib/i18n";

export function CommandPalette() {
  const open = useUi((s) => s.commandOpen);
  const setOpen = useUi((s) => s.setCommandOpen);
  const router = useRouter();
  const { setTheme } = useTheme();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(!open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  if (!open) return null;

  const go = (href: string) => {
    router.push(href);
    setOpen(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-[18vh]" onClick={() => setOpen(false)}>
      <Command className="w-[min(520px,calc(100vw-24px))] overflow-hidden rounded-md border border-border bg-popover shadow-xl" onClick={(e) => e.stopPropagation()}>
        <Command.Input
          placeholder={t.commandPlaceholder}
          className="h-10 w-full border-b border-border bg-transparent px-3 text-[13px] outline-none"
        />
        <Command.List className="max-h-72 overflow-auto p-1">
          <Command.Empty className="px-3 py-6 text-center text-[12px] text-muted-foreground">{t.noMatch}</Command.Empty>
          <Command.Group heading={t.command.actions} className="px-1 py-1 text-[10px] text-muted-foreground">
            <Command.Item value={t.command.newProvider} onSelect={() => go("/providers?new=1")} className="cursor-pointer rounded-sm px-2 py-1.5 text-[12px] text-foreground data-[selected=true]:bg-accent">
              {t.command.newProvider}
            </Command.Item>
            <Command.Item value={t.command.newKey} onSelect={() => go("/api-keys?new=1")} className="cursor-pointer rounded-sm px-2 py-1.5 text-[12px] text-foreground data-[selected=true]:bg-accent">
              {t.command.newKey}
            </Command.Item>
            <Command.Item value={t.command.themeDark} onSelect={() => { setTheme("dark"); setOpen(false); }} className="cursor-pointer rounded-sm px-2 py-1.5 text-[12px] text-foreground data-[selected=true]:bg-accent">
              {t.command.themeDark}
            </Command.Item>
            <Command.Item value={t.command.themeLight} onSelect={() => { setTheme("light"); setOpen(false); }} className="cursor-pointer rounded-sm px-2 py-1.5 text-[12px] text-foreground data-[selected=true]:bg-accent">
              {t.command.themeLight}
            </Command.Item>
          </Command.Group>
          <Command.Group heading={t.command.pages} className="px-1 py-1 text-[10px] text-muted-foreground">
            {navItems.map((item) => (
              <Command.Item
                key={item.href}
                value={item.label}
                onSelect={() => go(item.href)}
                className="cursor-pointer rounded-sm px-2 py-1.5 text-[12px] text-foreground data-[selected=true]:bg-accent"
              >
                {item.label}
              </Command.Item>
            ))}
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  );
}

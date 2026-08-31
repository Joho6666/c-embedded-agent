"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useUi } from "@/lib/stores/ui";
import { useGateway } from "@/lib/stores/gateway";
import { navItems } from "./nav";
import { copyText } from "@/lib/format";
import { toast } from "sonner";

export function CommandPalette() {
  const open = useUi((s) => s.commandOpen);
  const setOpen = useUi((s) => s.setCommandOpen);
  const router = useRouter();
  const url = useGateway((s) => s.settings.gatewayUrl);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(!open);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50" onClick={() => setOpen(false)}>
      <div
        className="mx-auto mt-[12vh] w-[min(520px,calc(100vw-24px))] overflow-hidden rounded-md border border-border bg-card shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-border px-3 py-2 text-[11px] text-muted-foreground">跳转 · Ctrl+K</div>
        <div className="max-h-80 overflow-auto p-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.href}
                className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-[12px] hover:bg-accent"
                onClick={() => {
                  router.push(item.href);
                  setOpen(false);
                }}
              >
                <Icon className="size-3.5 text-muted-foreground" />
                {item.label}
              </button>
            );
          })}
          <button
            className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-[12px] hover:bg-accent"
            onClick={async () => {
              await copyText(url);
              toast.success("已复制 Gateway URL");
              setOpen(false);
            }}
          >
            复制 Gateway URL
          </button>
        </div>
      </div>
    </div>
  );
}

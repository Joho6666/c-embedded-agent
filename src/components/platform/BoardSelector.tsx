"use client";

import type { PlatformDefinition } from "@/types/platform";
import { CapabilityBadge } from "./CapabilityBadge";
import { cn } from "@/lib/utils";

export function BoardSelector({
  platform,
  mcu,
  board,
  onChange,
}: {
  platform: PlatformDefinition;
  mcu: string;
  board: string;
  onChange: (next: { mcu: string; board: string }) => void;
}) {
  return (
    <div className="space-y-1">
      {platform.boards.map((b) => (
        <button
          key={b.id}
          type="button"
          onClick={() => onChange({ mcu: b.mcu, board: b.label })}
          className={cn(
            "flex w-full items-center justify-between rounded-sm border px-3 py-2 text-left",
            mcu === b.mcu && board === b.label ? "border-primary bg-accent" : "border-border",
          )}
        >
          <span>
            <span className="font-mono text-[12px]">{b.mcu}</span>
            <span className="ml-2 text-[11px] text-muted-foreground">{b.label}</span>
          </span>
          <span className="flex items-center gap-2">
            <span className="text-[11px] text-muted-foreground">
              {b.flashKb} KB / {b.ramKb} KB
            </span>
            {b.status && <CapabilityBadge status={b.status} />}
          </span>
        </button>
      ))}
    </div>
  );
}

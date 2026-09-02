"use client";

import { PLATFORMS } from "@/lib/platform";
import { CapabilityBadge } from "./CapabilityBadge";
import { cn } from "@/lib/utils";
import type { PlatformId } from "@/types/platform";

export function PlatformSelector({
  value,
  onChange,
}: {
  value: PlatformId;
  onChange: (id: PlatformId) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
      {PLATFORMS.map((p) => (
        <button
          key={p.id}
          type="button"
          onClick={() => onChange(p.id)}
          className={cn(
            "rounded-md border px-3 py-3 text-left",
            value === p.id ? "border-primary bg-accent" : "border-border bg-background",
          )}
        >
          <div className="flex items-center justify-between gap-1">
            <span className="text-[13px] font-medium">{p.label}</span>
            <CapabilityBadge status={p.status} />
          </div>
          <div className="mt-1 text-[11px] text-muted-foreground">{p.architecture}</div>
        </button>
      ))}
    </div>
  );
}

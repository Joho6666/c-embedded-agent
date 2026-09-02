"use client";

import type { NamedOption } from "@/types/platform";
import { CapabilityBadge } from "./CapabilityBadge";
import { cn } from "@/lib/utils";

export function OptionGrid({
  options,
  value,
  onChange,
}: {
  options: NamedOption[];
  value: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {options.map((o) => (
        <button
          key={o.id}
          type="button"
          onClick={() => onChange(o.id)}
          className={cn("rounded-sm border px-3 py-3 text-left text-[12px]", value === o.id ? "border-primary bg-accent" : "border-border")}
        >
          <div className="flex items-center justify-between gap-1">
            <span>{o.label}</span>
            {o.status && o.status !== "supported" && <CapabilityBadge status={o.status} />}
          </div>
        </button>
      ))}
    </div>
  );
}

export function ToolchainSelector(props: { options: NamedOption[]; value: string; onChange: (id: string) => void }) {
  return <OptionGrid {...props} />;
}

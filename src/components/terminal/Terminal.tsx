"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

export function Terminal({ lines, className }: { lines: string[]; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines]);

  return (
    <div
      ref={ref}
      className={cn(
        "terminal h-full overflow-auto bg-terminal px-3 py-2 text-[12px] leading-5 text-zinc-300",
        className,
      )}
    >
      {lines.map((line, i) => (
        <div
          key={`${i}-${line.slice(0, 24)}`}
          className={cn(
            line.toLowerCase().includes("error") && "text-error",
            line.toLowerCase().includes("success") && "text-success",
            line.startsWith("$") && "text-info",
          )}
        >
          {line}
        </div>
      ))}
    </div>
  );
}

"use client";

import { ToolCard } from "@/components/tools/ToolCard";
import { tools } from "@/lib/mock/tools";
import type { ToolItem } from "@/types/tools";

const groups: ToolItem["group"][] = [
  "Compiler",
  "Code Intelligence",
  "Static Analysis",
  "Testing",
  "Hardware",
  "Serial",
  "Git",
];

export default function ToolsPage() {
  return (
    <div className="p-5">
      <h1 className="text-[18px] font-semibold">工具</h1>
      <p className="text-[12px] text-muted-foreground">Agent 可调用的编译器、分析、烧录与串口工具</p>
      {groups.map((g) => (
        <section key={g} className="mt-5">
          <h2 className="mb-2 text-[12px] font-medium text-muted-foreground">{g}</h2>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {tools
              .filter((t) => t.group === g)
              .map((t) => (
                <ToolCard key={t.id} tool={t} />
              ))}
          </div>
        </section>
      ))}
    </div>
  );
}

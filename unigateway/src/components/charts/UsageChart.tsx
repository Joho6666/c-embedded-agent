"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TimePoint } from "@/types";
import { formatCompact } from "@/lib/format";
import { gridStroke, tooltipStyle } from "./chart-theme";

export function UsageChart({ data, dataKey = "requests" }: { data: TimePoint[]; dataKey?: "requests" | "tokens" }) {
  return (
    <div className="h-[220px] w-full">
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={gridStroke} vertical={false} />
          <XAxis dataKey="t" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
          <YAxis
            tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
            axisLine={false}
            tickLine={false}
            width={40}
            tickFormatter={(v) => formatCompact(Number(v))}
          />
          <Tooltip contentStyle={tooltipStyle} formatter={(v) => formatCompact(Number(v))} />
          <Area type="monotone" dataKey={dataKey} stroke="var(--foreground)" fill="var(--muted)" strokeWidth={1.4} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

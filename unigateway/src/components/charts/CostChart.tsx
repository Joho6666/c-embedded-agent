"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TimePoint } from "@/types";
import { formatUsd } from "@/lib/format";
import { gridStroke, tooltipStyle } from "./chart-theme";

export function CostChart({ data }: { data: TimePoint[] }) {
  return (
    <div className="h-[220px] w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={gridStroke} vertical={false} />
          <XAxis dataKey="t" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
          <YAxis
            tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
            axisLine={false}
            tickLine={false}
            width={44}
            tickFormatter={(v) => `$${v}`}
          />
          <Tooltip contentStyle={tooltipStyle} formatter={(v) => formatUsd(Number(v))} />
          <Line type="monotone" dataKey="cost" stroke="var(--foreground)" strokeWidth={1.4} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

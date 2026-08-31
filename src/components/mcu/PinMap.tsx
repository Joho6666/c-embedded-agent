import type { PinConfig } from "@/types/mcu";
import { cn } from "@/lib/utils";

export function PinMap({ pins }: { pins: PinConfig[] }) {
  const left = pins.filter((p) => p.side === "left");
  const right = pins.filter((p) => p.side === "right");
  const top = pins.filter((p) => p.side === "top");
  const bottom = pins.filter((p) => p.side === "bottom");

  return (
    <div>
      <h2 className="mb-3 text-[12px] font-medium text-muted-foreground">Pin Configuration</h2>
      <div className="grid items-center gap-3 lg:grid-cols-[1fr_220px_1fr]">
        <div className="space-y-1">
          {left.map((p) => (
            <PinRow key={p.name} pin={p} align="right" />
          ))}
        </div>
        <div className="mx-auto flex aspect-square w-[220px] flex-col items-center justify-between rounded-sm border border-border bg-panel-2 p-3">
          <div className="flex flex-wrap justify-center gap-1">
            {top.map((p) => (
              <span key={p.name} className="font-mono text-[9px] text-muted-foreground">
                {p.name}
              </span>
            ))}
          </div>
          <div className="text-center">
            <div className="font-mono text-[13px] font-semibold">STM32F103C8T6</div>
            <div className="text-[10px] text-muted-foreground">LQFP48</div>
          </div>
          <div className="flex flex-wrap justify-center gap-1">
            {bottom.map((p) => (
              <span key={p.name} className="font-mono text-[9px] text-muted-foreground">
                {p.name}
              </span>
            ))}
          </div>
        </div>
        <div className="space-y-1">
          {right.map((p) => (
            <PinRow key={p.name} pin={p} align="left" />
          ))}
        </div>
      </div>
      <div className="mt-4 overflow-auto rounded-sm border border-border">
        <table className="w-full text-left text-[12px]">
          <thead className="bg-muted text-[11px] text-muted-foreground">
            <tr>
              <th className="px-3 py-1.5">Pin</th>
              <th className="px-3 py-1.5">Functions</th>
              <th className="px-3 py-1.5">Assigned</th>
              <th className="px-3 py-1.5">Note</th>
            </tr>
          </thead>
          <tbody>
            {pins.map((p) => (
              <tr key={p.name} className={cn("border-t border-border", p.highlight && "bg-success/10")}>
                <td className="px-3 py-1.5 font-mono">{p.name}</td>
                <td className="px-3 py-1.5 text-muted-foreground">{p.functions.join(" / ")}</td>
                <td className="px-3 py-1.5">{p.assigned ?? "—"}</td>
                <td className="px-3 py-1.5">{p.note ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PinRow({ pin, align }: { pin: PinConfig; align: "left" | "right" }) {
  return (
    <div className={cn("flex items-center gap-2 text-[11px]", align === "right" && "justify-end")}>
      {align === "right" && (
        <span className={cn("truncate", pin.highlight && "text-success")}>
          {pin.assigned ?? pin.functions[0]}
        </span>
      )}
      <span
        className={cn(
          "inline-flex min-w-12 justify-center rounded-sm border border-border bg-panel px-1 font-mono",
          pin.highlight && "border-success text-success",
        )}
      >
        {pin.name}
      </span>
      {align === "left" && (
        <span className={cn("truncate", pin.highlight && "text-success")}>
          {pin.assigned ?? pin.functions[0]}
          {pin.note ? ` · ${pin.note}` : ""}
        </span>
      )}
    </div>
  );
}

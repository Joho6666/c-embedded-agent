import type { IocClockTree } from "@/types/ioc";

function mhz(hz?: number) {
  if (!hz) return "—";
  return `${Math.round(hz / 1_000_000)}MHz`;
}

export function ClockTree({ clock }: { clock?: IocClockTree }) {
  if (!clock) {
    return <div className="text-[12px] text-muted-foreground">无时钟数据</div>;
  }
  const rows = [
    ["HSE", mhz(clock.hseHz)],
    ["PLL", clock.pllMul ? `×${clock.pllMul}` : "—"],
    ["SYSCLK", mhz(clock.sysclkHz)],
    ["AHB", mhz(clock.ahbHz)],
    ["APB1", mhz(clock.apb1Hz)],
    ["APB2", mhz(clock.apb2Hz)],
  ];
  return (
    <div className="font-mono text-[12px]">
      <div className="text-[11px] text-muted-foreground">Clock Tree</div>
      <div className="mt-2 space-y-1">
        {rows.map(([k, v], i) => (
          <div key={k}>
            <div className="flex justify-between rounded-sm border border-border bg-panel px-2 py-1.5">
              <span className="text-muted-foreground">{k}</span>
              <span>{v}</span>
            </div>
            {i < rows.length - 1 && <div className="py-0.5 text-center text-[10px] text-muted-foreground">↓</div>}
          </div>
        ))}
      </div>
    </div>
  );
}

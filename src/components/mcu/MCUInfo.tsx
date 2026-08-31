import type { McuInfo } from "@/types/mcu";

export function MCUInfo({ mcu }: { mcu: McuInfo }) {
  const specs = [
    ["Core", mcu.core],
    ["Frequency", mcu.frequency],
    ["Flash", `${mcu.flashKb} KB`],
    ["RAM", `${mcu.ramKb} KB`],
    ["Voltage", mcu.voltage],
    ["Package", mcu.package],
  ];
  return (
    <div>
      <div className="text-[11px] text-muted-foreground">当前芯片</div>
      <h1 className="mt-1 font-mono text-[22px] font-semibold tracking-tight">{mcu.name}</h1>
      <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-3">
        {specs.map(([k, v]) => (
          <div key={k} className="rounded-sm border border-border bg-panel p-3">
            <div className="text-[11px] text-muted-foreground">{k}</div>
            <div className="mt-1 text-[13px] font-medium">{v}</div>
          </div>
        ))}
      </div>
      <h2 className="mt-6 text-[12px] font-medium text-muted-foreground">Peripheral Overview</h2>
      <div className="mt-2 grid grid-cols-4 gap-2 md:grid-cols-8">
        {mcu.peripherals.map((p) => (
          <div key={p.name} className="rounded-sm border border-border bg-panel p-2 text-center">
            <div className="font-mono text-[16px]">{p.count}</div>
            <div className="text-[11px] text-muted-foreground">{p.name}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

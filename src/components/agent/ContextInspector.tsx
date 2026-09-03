"use client";

import { useEditor } from "@/lib/stores/editor-store";
import { useHardware } from "@/lib/stores/hardware-store";
import { useAgent } from "@/lib/stores/agent-store";

export function ContextInspector() {
  const ctx = useHardware((s) => s.context);
  const ioc = useHardware((s) => s.ioc);
  const files = useEditor((s) => Object.keys(s.files).length);
  const diags = useAgent((s) => s.diagnostics.length);
  const skills = ioc
    ? [
        ioc.usart.length ? "USART" : null,
        ioc.tim.length ? "TIM" : null,
        ioc.pwm.length ? "PWM" : "GPIO",
      ].filter(Boolean)
    : ["GPIO"];
  const memories = useAgent((s) => s.diagnostics.filter((d) => /undefined reference|undeclared/i.test(d.message)).length);

  const rows: [string, string][] = [
    ["Target", ctx.mcu],
    ["Board", ctx.board],
    ["Clock", ctx.clock],
    ["Files", String(files)],
    ["Knowledge", ctx.evidence?.length ? String(ctx.evidence.length) : ioc ? "ioc + board" : "board profile"],
    ["Skills", skills.join(" · ") || "—"],
    ["Error Memories", String(memories)],
    ["Compiler Diagnostics", String(diags)],
  ];

  return (
    <div>
      <div className="border-b border-border px-3 py-2 text-[11px] font-medium text-muted-foreground">Context</div>
      <dl className="space-y-1.5 p-3 text-[12px]">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-2">
            <dt className="text-muted-foreground">{k}</dt>
            <dd className="text-right font-mono">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

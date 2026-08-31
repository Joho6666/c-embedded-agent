"use client";

import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="text-[18px] font-semibold">设置</h1>
      <p className="text-[12px] text-muted-foreground">主题、工具链与快捷键</p>

      <section className="mt-6 rounded-sm border border-border bg-panel p-4">
        <h2 className="text-[13px] font-medium">主题</h2>
        <p className="mt-1 text-[12px] text-muted-foreground">默认 Dark Mode</p>
        <div className="mt-3 flex gap-2">
          <Button variant={theme === "dark" ? "default" : "outline"} onClick={() => setTheme("dark")}>
            Dark
          </Button>
          <Button variant={theme === "light" ? "default" : "outline"} onClick={() => setTheme("light")}>
            Light
          </Button>
        </div>
      </section>

      <section className="mt-4 rounded-sm border border-border bg-panel p-4">
        <h2 className="text-[13px] font-medium">默认工具链</h2>
        <div className="mt-3 grid grid-cols-2 gap-2 text-[12px]">
          <Field k="Compiler" v="ARM GCC 13.2" />
          <Field k="Framework" v="STM32 HAL" />
          <Field k="Debugger" v="OpenOCD / ST-Link" />
          <Field k="Serial" v="COM3 115200" />
        </div>
      </section>

      <section className="mt-4 rounded-sm border border-border bg-panel p-4">
        <h2 className="text-[13px] font-medium">编辑器</h2>
        <div className="mt-3 grid grid-cols-2 gap-2 text-[12px]">
          <Field k="字体" v="Geist Mono / JetBrains Mono" />
          <Field k="字号" v="12" />
          <Field k="Tab" v="4 spaces" />
          <Field k="语言" v="中文 UI · 英文术语" />
        </div>
      </section>

      <section className="mt-4 rounded-sm border border-border bg-panel p-4">
        <h2 className="text-[13px] font-medium">快捷键</h2>
        <ul className="mt-3 space-y-1 font-mono text-[12px] text-muted-foreground">
          <li>Ctrl + K · Agent Command</li>
          <li>Ctrl + B · Build</li>
          <li>Ctrl + Shift + F · Flash</li>
          <li>Ctrl + ` · Terminal</li>
        </ul>
      </section>
    </div>
  );
}

function Field({ k, v }: { k: string; v: string }) {
  return (
    <div className="rounded-sm border border-border bg-panel-2 px-2 py-1.5">
      <div className="text-[11px] text-muted-foreground">{k}</div>
      <div>{v}</div>
    </div>
  );
}

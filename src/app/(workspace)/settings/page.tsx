"use client";

import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="text-[18px] font-semibold">设置</h1>
      <p className="text-[12px] text-muted-foreground">主题、工具链与快捷键</p>
      <section className="mt-6 rounded-md border border-border bg-panel p-4">
        <h2 className="text-[13px] font-medium">主题</h2>
        <p className="mt-1 text-[12px] text-muted-foreground">默认深色模式</p>
        <div className="mt-3 flex gap-2">
          <Button variant={theme === "dark" ? "default" : "outline"} onClick={() => setTheme("dark")}>
            深色
          </Button>
          <Button variant={theme === "light" ? "default" : "outline"} onClick={() => setTheme("light")}>
            浅色
          </Button>
        </div>
      </section>
      <section className="mt-4 rounded-md border border-border bg-panel p-4">
        <h2 className="text-[13px] font-medium">快捷键</h2>
        <ul className="mt-2 space-y-1 font-mono text-[12px] text-muted-foreground">
          <li>Ctrl + K · 命令面板</li>
          <li>Ctrl + S · 保存</li>
          <li>Ctrl + B · 构建</li>
          <li>Ctrl + Shift + F · 烧录</li>
          <li>Ctrl + ` · 终端</li>
        </ul>
      </section>
      <section className="mt-4 rounded-md border border-border bg-panel p-4 text-[12px] text-muted-foreground">
        后端：{process.env.NEXT_PUBLIC_API_URL || "MockBackend（未配置 NEXT_PUBLIC_API_URL）"}
      </section>
    </div>
  );
}

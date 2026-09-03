"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Cpu, FileCode, FolderOpen, FolderPlus, LayoutTemplate } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";
import { StatusBadge } from "@/components/common/StatusBadge";
import { StatusDot } from "@/components/common/StatusDot";
import { CapabilityBadge } from "@/components/platform/CapabilityBadge";
import { listProjects } from "@/lib/api/project";
import { getEnvironment, type EnvironmentItem } from "@/lib/api/environment";
import { getDevices, type DeviceItem, type DevicesPayload } from "@/lib/api/devices";
import { useLive } from "@/lib/stores/live-store";
import { useProject } from "@/lib/stores/project-store";
import { useHardware } from "@/lib/stores/hardware-store";
import { PLATFORMS } from "@/lib/platform";
import type { Project } from "@/types/project";
import { cn } from "@/lib/utils";

const QUICK: Array<{ href: string; label: string; hint?: string; icon: typeof FolderPlus }> = [
  { href: "/projects/new", label: "新建项目", icon: FolderPlus },
  { href: "/projects/new?mode=existing", label: "打开本地工程", hint: "Coming Soon", icon: FolderOpen },
  { href: "/projects/new?mode=ioc", label: "导入 CubeMX", icon: Cpu },
  { href: "/projects/new?platform=esp32", label: "导入 ESP-IDF", hint: "Coming Soon", icon: LayoutTemplate },
  { href: "/projects/new?platform=stm32", label: "导入 PlatformIO", hint: "Coming Soon", icon: LayoutTemplate },
  { href: "/projects/new?platform=c51", label: "导入 Keil", hint: "Coming Soon", icon: LayoutTemplate },
  { href: "/projects/new?platform=host-c", label: "导入普通 C 项目", hint: "Coming Soon", icon: FileCode },
];

export function StartCenter() {
  const router = useRouter();
  const mode = useLive((s) => s.mode);
  const setProjectId = useProject((s) => s.setProjectId);
  const setContext = useHardware((s) => s.setContext);
  const [idea, setIdea] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [env, setEnv] = useState<EnvironmentItem[]>([]);
  const [devices, setDevices] = useState<DevicesPayload | null>(null);

  useEffect(() => {
    void listProjects().then(setProjects);
    void getEnvironment().then((r) => setEnv(r.items));
    void getDevices().then(setDevices);
  }, [mode]);

  return (
    <div className="h-full overflow-auto">
      <div className="mx-auto grid max-w-[1280px] gap-4 p-5 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.9fr)]">
        <section className="rounded-md border border-border bg-panel p-5">
          <div className="text-[11px] text-muted-foreground">C-Agent Workbench 2.0</div>
          <h1 className="mt-1 text-[22px] font-semibold tracking-tight">欢迎使用 C-Agent Workbench 2.0</h1>
          <p className="mt-1 text-[13px] text-muted-foreground">描述一个 C 或嵌入式项目，从这里开始工程，而不是打开一张仪表盘。</p>

          <label className="mt-4 block text-[11px] text-muted-foreground">AI Project Intake</label>
          <textarea
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            rows={5}
            className="mt-1 w-full resize-none rounded-md border border-border bg-background px-3 py-2 text-[13px] outline-none focus:ring-1 focus:ring-ring"
            placeholder={"描述你的 C 或嵌入式项目想法\n例如：\n使用 ESP32-S3 + ESP-IDF\n制作一个温湿度采集节点，\n通过 MQTT 上传云端。"}
          />
          <div className="mt-2 flex gap-2">
            <Button
              onClick={() => {
                const q = new URLSearchParams();
                if (idea.trim()) q.set("idea", idea.trim());
                router.push(`/projects/new?${q.toString()}`);
              }}
            >
              开始配置工程
            </Button>
            <Button variant="outline" asChild>
              <Link href="/projects">打开项目列表</Link>
            </Button>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4">
            {QUICK.map((q) => (
              <Link
                key={q.label}
                href={q.href}
                className="rounded-md border border-border bg-background px-3 py-2.5 hover:border-primary/50 hover:bg-accent/40"
              >
                <q.icon className="size-3.5 text-muted-foreground" />
                <div className="mt-1 text-[12px] font-medium">{q.label}</div>
                {q.hint && <div className="text-[10px] text-warning">{q.hint}</div>}
              </Link>
            ))}
          </div>
        </section>

        <aside className="space-y-4">
          <section className="rounded-md border border-border bg-panel p-3">
            <h2 className="text-[12px] font-medium">Environment</h2>
            {mode !== "live" && (
              <div className="mt-2">
                <CapabilityBanner reason="未连接 LIVE 后端。工具状态为 UNKNOWN，不会显示全部正常。" />
              </div>
            )}
            <ul className="mt-2 space-y-1">
              {env.map((item) => (
                <li key={item.id} className="flex items-center justify-between gap-2 text-[12px]">
                  <span className="flex items-center gap-2">
                    <StatusDot status={item.status} />
                    {item.label}
                  </span>
                  <StatusBadge status={item.status} />
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-md border border-border bg-panel p-3">
            <h2 className="text-[12px] font-medium">Connected Devices</h2>
            <ul className="mt-2 space-y-1">
              {(devices?.probes ?? []).concat(devices?.ports ?? []).map((d: DeviceItem) => (
                <li key={d.id + d.label} className="flex items-center justify-between gap-2 text-[12px]">
                  <span className="flex items-center gap-2">
                    <StatusDot status={d.presence} />
                    {d.label}
                  </span>
                  <StatusBadge status={d.presence} />
                </li>
              ))}
            </ul>
          </section>
        </aside>

        <section className="rounded-md border border-border bg-panel p-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="text-[13px] font-medium">Recent Projects</h2>
            <Link href="/projects" className="text-[11px] text-primary">
              全部
            </Link>
          </div>
          {projects.length === 0 ? (
            <p className="mt-3 text-[12px] text-muted-foreground">
              {mode === "live" ? "还没有工程。用新建项目或导入 CubeMX 开始。" : "DEMO / 离线不列出本地工程。"}
            </p>
          ) : (
            <div className="mt-3 overflow-auto">
              <table className="w-full text-left text-[12px]">
                <thead className="text-[11px] text-muted-foreground">
                  <tr>
                    <th className="py-1 font-medium">项目</th>
                    <th className="font-medium">平台</th>
                    <th className="font-medium">板卡</th>
                    <th className="font-medium">Workspace</th>
                    <th className="font-medium">构建</th>
                  </tr>
                </thead>
                <tbody>
                  {projects.slice(0, 8).map((p) => (
                    <tr key={p.id} className="border-t border-border">
                      <td className="py-1.5">
                        <button
                          className="text-left hover:text-primary"
                          onClick={() => {
                            setProjectId(p.id);
                            setContext({ mcu: p.mcu, platform: p.platform, framework: p.framework, board: p.board, buildTool: p.compiler });
                            router.push("/workspace");
                          }}
                        >
                          {p.name}
                        </button>
                      </td>
                      <td>{p.platform}</td>
                      <td>{p.board || p.description || "—"}</td>
                      <td className="font-mono text-[11px]">{p.workspacePath || p.id}</td>
                      <td>
                        <StatusBadge status={p.buildStatus} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="rounded-md border border-border bg-panel p-4 lg:col-span-2">
          <h2 className="text-[13px] font-medium">Templates</h2>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            {PLATFORMS.filter((p) => p.id !== "rp2040").map((p) => (
              <Link
                key={p.id}
                href={`/projects/new?platform=${p.id}`}
                className={cn("rounded-md border border-border bg-background p-3 hover:border-primary/50", !p.supported && "opacity-90")}
              >
                <div className="flex items-center justify-between">
                  <div className="text-[13px] font-medium">{p.label}</div>
                  <CapabilityBadge status={p.status} />
                </div>
                <div className="mt-1 font-mono text-[11px] text-muted-foreground">{p.defaultMcu}</div>
                <p className="mt-2 text-[11px] text-muted-foreground">{p.statusNote}</p>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

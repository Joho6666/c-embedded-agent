"use client";

import { Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";
import { CapabilityBadge } from "@/components/platform/CapabilityBadge";
import { PlatformSelector } from "@/components/platform/PlatformSelector";
import { BoardSelector } from "@/components/platform/BoardSelector";
import { OptionGrid } from "@/components/platform/ToolchainSelector";
import { analyzeIoc, importIoc, importExistingProject } from "@/lib/api/ioc";
import { createRemoteProject } from "@/lib/api/project";
import { getPlatform, normalizePlatformId } from "@/lib/platform";
import { useHardware } from "@/lib/stores/hardware-store";
import { useProject } from "@/lib/stores/project-store";
import { useLive } from "@/lib/stores/live-store";
import type { PlatformId } from "@/types/platform";
import type { IocAnalysis } from "@/types/ioc";
import { cn } from "@/lib/utils";

type CreateMode = "new" | "ioc" | "existing";

export default function NewProjectPage() {
  return (
    <Suspense fallback={<div className="p-4 text-[12px] text-muted-foreground">加载工程配置…</div>}>
      <NewProjectForm />
    </Suspense>
  );
}

function NewProjectForm() {
  const router = useRouter();
  const params = useSearchParams();
  const setContext = useHardware((s) => s.setContext);
  const setIoc = useHardware((s) => s.setIoc);
  const setProjectId = useProject((s) => s.setProjectId);
  const live = useLive((s) => s.mode);
  const initialPlatform = normalizePlatformId(params.get("platform") || "stm32");
  const initialMode = (params.get("mode") as CreateMode) || "new";
  const idea = params.get("idea") || "";

  const [mode, setMode] = useState<CreateMode>(initialMode);
  const [platformId, setPlatformId] = useState<PlatformId>(initialPlatform);
  const platform = getPlatform(platformId);
  const [name, setName] = useState("Blink_UART_STM32F103");
  const [workspace, setWorkspace] = useState("C:/work/c-agent/projects");
  const [cstd, setCstd] = useState("C11");
  const [description, setDescription] = useState(idea);
  const [mcu, setMcu] = useState(platform.defaultMcu);
  const [board, setBoard] = useState(platform.defaultBoard);
  const [framework, setFramework] = useState(platform.defaultFramework);
  const [toolchain, setToolchain] = useState(platform.defaultToolchain);
  const [flash, setFlash] = useState(platform.flashAdapters[0]?.id ?? "");
  const [debug, setDebug] = useState(platform.debugAdapters[0]?.id ?? "");
  const [port, setPort] = useState("");
  const [baud, setBaud] = useState("115200");
  const [skills, setSkills] = useState<string[]>(["GPIO", "UART"]);
  const [iocName, setIocName] = useState("");
  const [iocText, setIocText] = useState("");
  const [preview, setPreview] = useState<IocAnalysis | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onPlatform = (id: PlatformId) => {
    const next = getPlatform(id);
    setPlatformId(id);
    setMcu(next.defaultMcu);
    setBoard(next.defaultBoard);
    setFramework(next.defaultFramework);
    setToolchain(next.defaultToolchain);
    setFlash(next.flashAdapters[0]?.id ?? "");
    setDebug(next.debugAdapters[0]?.id ?? "");
    setSkills(next.skills.filter((s) => ["GPIO", "UART"].includes(s)));
  };

  const tree = useMemo(() => {
    if (platformId === "stm32") return ["Core/Src/main.c", "Core/Inc/main.h", "Drivers/", "Makefile", "cagent.yaml"];
    if (platformId === "esp32") return ["main/main.c", "CMakeLists.txt", "sdkconfig", "cagent.yaml"];
    if (platformId === "c51") return ["src/main.c", "include/", "Makefile", "cagent.yaml"];
    if (platformId === "host-c") return ["src/main.c", "CMakeLists.txt", "tests/", "cagent.yaml"];
    return ["src/main.c", "CMakeLists.txt"];
  }, [platformId]);

  const selectedBoard = platform.boards.find((b) => b.mcu === mcu) ?? platform.boards[0];

  const applyHardware = () => {
    setContext({
      platform: platform.label,
      mcu,
      board,
      framework,
      buildTool: toolchain,
      clock: selectedBoard?.clock,
      flashKb: selectedBoard?.flashKb,
      ramKb: selectedBoard?.ramKb,
      core: selectedBoard?.architecture,
      debugger: platform.debugAdapters.find((d) => d.id === debug)?.label,
      serialPort: port,
      serialBaud: Number(baud) || 115200,
    });
  };

  const create = async () => {
    setBusy(true);
    setErr(null);
    try {
      applyHardware();
      const canBackend = live === "live" && platform.supported && framework === "HAL" && /F103/.test(mcu);
      if (canBackend) {
        const created = await createRemoteProject({ name, mcu, framework });
        if (created) setProjectId(created.id);
      }
      router.push("/workspace");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="h-full overflow-auto">
      <div className="grid h-full min-h-[640px] lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]">
        <div className="space-y-5 overflow-auto p-5">
          <div>
            <div className="text-[11px] text-muted-foreground">C-Agent Workbench 2.0</div>
            <h1 className="text-[20px] font-semibold">新建嵌入式工程</h1>
          </div>

          <div className="grid grid-cols-3 gap-2">
            {(
              [
                ["new", "新建工程"],
                ["ioc", "导入 CubeMX"],
                ["existing", "导入已有工程"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setMode(id)}
                className={cn("rounded-sm border px-3 py-2 text-[12px]", mode === id ? "border-primary bg-accent" : "border-border")}
              >
                {label}
              </button>
            ))}
          </div>

          {mode === "ioc" && (
            <section className="space-y-3">
              <input type="file" accept=".ioc" onChange={(e) => void e.target.files?.[0]?.text().then((t) => {
                const f = e.target.files?.[0];
                if (!f) return;
                setIocName(f.name);
                setIocText(t);
                void analyzeIoc(t, f.name).then((r) => {
                  if (r.available && r.analysis) setPreview(r.analysis);
                  else setErr(r.reason ?? "Backend Not Implemented");
                });
              })} />
              {preview && <div className="font-mono text-[12px]">{preview.mcu} · {preview.board}</div>}
              {err && <CapabilityBanner reason={err} />}
              <Button
                disabled={!iocText || live !== "live"}
                onClick={() => {
                  void importIoc(iocText, iocName).then((r) => {
                    if (!r.available) {
                      setErr(r.reason ?? "Backend Not Implemented");
                      return;
                    }
                    if (r.analysis) setIoc(r.analysis);
                    if (r.projectId) setProjectId(r.projectId);
                    router.push("/ioc");
                  });
                }}
              >
                导入并打开 IOC
              </Button>
            </section>
          )}

          {mode === "existing" && (
            <section className="space-y-3">
              <CapabilityBanner reason="打开本地工程 / ZIP 导入本轮为 Coming Soon。" />
              <Button variant="outline" onClick={() => void importExistingProject().then((r) => setErr(r.reason ?? "Backend Not Implemented"))}>
                选择工程
              </Button>
              {err && <CapabilityBanner reason={err} />}
            </section>
          )}

          {mode === "new" && (
            <>
              <section>
                <h2 className="mb-2 text-[12px] font-medium">Target Platform</h2>
                <PlatformSelector
                  value={platformId}
                  onChange={onPlatform}
                />
              </section>

              <section className="grid gap-3 sm:grid-cols-2">
                <Field label="项目名称" value={name} onChange={setName} />
                <Field label="工作区" value={workspace} onChange={setWorkspace} />
                <label className="text-[11px] text-muted-foreground">
                  C 标准
                  <select className="mt-1 h-8 w-full rounded-sm border border-border bg-panel px-2 text-[12px]" value={cstd} onChange={(e) => setCstd(e.target.value)}>
                    <option>C11</option>
                    <option>C99</option>
                    <option>C17</option>
                  </select>
                </label>
                <label className="text-[11px] text-muted-foreground sm:col-span-2">
                  描述
                  <textarea className="mt-1 h-16 w-full rounded-sm border border-border bg-panel px-2 py-1 text-[12px]" value={description} onChange={(e) => setDescription(e.target.value)} />
                </label>
              </section>

              <section>
                <h2 className="mb-2 text-[12px] font-medium">MCU / Board</h2>
                <BoardSelector platform={platform} mcu={mcu} board={board} onChange={(n) => { setMcu(n.mcu); setBoard(n.board); }} />
              </section>

              <section>
                <h2 className="mb-2 text-[12px] font-medium">Framework / SDK</h2>
                <OptionGrid options={platform.frameworks} value={framework} onChange={setFramework} />
              </section>

              <section>
                <h2 className="mb-2 text-[12px] font-medium">Toolchain</h2>
                <OptionGrid options={platform.toolchains} value={toolchain} onChange={setToolchain} />
              </section>

              {platform.flashAdapters.length > 0 && (
                <section>
                  <h2 className="mb-2 text-[12px] font-medium">Flash</h2>
                  <OptionGrid options={platform.flashAdapters} value={flash} onChange={setFlash} />
                </section>
              )}

              {platform.debugAdapters.length > 0 && (
                <section>
                  <h2 className="mb-2 text-[12px] font-medium">Debug</h2>
                  <OptionGrid options={platform.debugAdapters} value={debug} onChange={setDebug} />
                </section>
              )}

              {platform.serialCapabilities && (
                <section className="grid grid-cols-2 gap-2">
                  <Field label="Port" value={port} onChange={setPort} placeholder="COM5" />
                  <Field label="Baud" value={baud} onChange={setBaud} />
                </section>
              )}

              <section>
                <h2 className="mb-2 text-[12px] font-medium">Skills</h2>
                <div className="flex flex-wrap gap-1">
                  {platform.skills.map((s) => {
                    const on = skills.includes(s);
                    return (
                      <button
                        key={s}
                        type="button"
                        onClick={() => setSkills((xs) => (on ? xs.filter((x) => x !== s) : [...xs, s]))}
                        className={cn("rounded-sm border px-2 py-1 text-[11px]", on ? "border-primary bg-accent" : "border-border")}
                      >
                        {s}
                      </button>
                    );
                  })}
                  {platform.skills.length === 0 && <span className="text-[11px] text-muted-foreground">Host C 无 MCU 外设 Skills</span>}
                </div>
              </section>

              {!platform.supported && (
                <CapabilityBanner reason={`${platform.label} 为 ${platform.status}。可以创建 UI Preview 工程，不会生成可编译固件。`} />
              )}

              <div className="flex justify-end gap-2 pb-6">
                <Button variant="outline" onClick={() => router.push("/")}>
                  取消
                </Button>
                <Button disabled={busy} onClick={() => void create()}>
                  {platform.supported ? "创建工程" : "创建 UI Preview"}
                </Button>
              </div>
            </>
          )}
        </div>

        <aside className="border-l border-border bg-panel p-4 text-[12px]">
          <h2 className="text-[13px] font-medium">工程预览</h2>
          <dl className="mt-3 space-y-1">
            <Row k="平台" v={platform.label} />
            <Row k="MCU" v={mcu} />
            <Row k="板卡" v={board} />
            <Row k="架构" v={selectedBoard?.architecture ?? platform.architecture} />
            <Row k="时钟" v={selectedBoard?.clock ?? "—"} />
            <Row k="Flash" v={selectedBoard ? `${selectedBoard.flashKb} KB` : "—"} />
            <Row k="RAM" v={selectedBoard ? `${selectedBoard.ramKb} KB` : "—"} />
            <Row k="框架" v={framework} />
            <Row k="工具链" v={toolchain} />
          </dl>
          <div className="mt-2">
            <CapabilityBadge status={platform.status} />
          </div>
          <h3 className="mt-4 text-[11px] text-muted-foreground">工程树</h3>
          <ul className="mt-1 font-mono text-[11px] text-muted-foreground">
            {tree.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
          <h3 className="mt-4 text-[11px] text-muted-foreground">已选 Skills</h3>
          <div className="mt-1 text-[11px]">{skills.join(" · ") || "—"}</div>
        </aside>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="text-[11px] text-muted-foreground">
      {label}
      <input
        className="mt-1 h-8 w-full rounded-sm border border-border bg-panel px-2 text-[12px] text-foreground"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-2">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className="font-mono">{v}</dd>
    </div>
  );
}

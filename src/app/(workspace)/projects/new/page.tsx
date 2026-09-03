"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { mcuCatalog } from "@/lib/mock/hardware";
import { useHardware } from "@/lib/stores/hardware-store";
import { useAgent } from "@/lib/stores/agent-store";
import { useProject } from "@/lib/stores/project-store";
import { cn } from "@/lib/utils";
import type { PlatformId } from "@/types/project";
import { analyzeIoc, importIoc, importExistingProject, scanExistingProject } from "@/lib/api/ioc";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";
import type { IocAnalysis } from "@/types/ioc";
import { useLive } from "@/lib/stores/live-store";
import { listPlatforms } from "@/lib/api/platforms";
import type { PlatformCapability } from "@/types/platform";

type CreateMode = "new" | "ioc" | "existing";

function applyIocToHardware(analysis: IocAnalysis, setContext: (c: Record<string, unknown>) => void, setIoc: (a: IocAnalysis) => void) {
  setIoc(analysis);
  const clock = analysis.clock?.sysclkHz ? `${Math.round(analysis.clock.sysclkHz / 1_000_000)} MHz` : undefined;
  const hse = analysis.clock?.hseHz ? `${Math.round(analysis.clock.hseHz / 1_000_000)} MHz` : undefined;
  setContext({
    mcu: analysis.mcu ?? "STM32F103C8T6",
    board: analysis.board ?? "Blue Pill",
    platform: "STM32",
    clock: clock ?? "72 MHz",
    hse,
    iocFilename: analysis.filename,
    projectGenerator: "STM32CubeMX",
    evidence: [
      { kind: "ioc", label: `CubeMX .ioc (${analysis.filename})` },
      { kind: "board", label: analysis.board ?? "Board Profile" },
      { kind: "rm0008", label: "RM0008" },
      { kind: "datasheet", label: "STM32F103 Datasheet" },
    ],
    pins: analysis.pins.map((p) => ({
      pin: p.pin,
      function: p.signal,
      peripheral: p.peripheral,
      direction: p.direction as "in" | "out" | "analog" | "af" | undefined,
      mode: p.mode,
      source: "user" as const,
    })),
  });
}

export default function NewProjectPage() {
  const router = useRouter();
  const setContext = useHardware((s) => s.setContext);
  const setIoc = useHardware((s) => s.setIoc);
  const start = useAgent((s) => s.startGoldenPath);
  const setProjectId = useProject((s) => s.setProjectId);
  const modeLive = useLive((s) => s.mode);
  const [mode, setMode] = useState<CreateMode>("new");
  const [step, setStep] = useState(1);
  const [platform, setPlatform] = useState<PlatformId>("STM32");
  const [mcu, setMcu] = useState("STM32F103C8T6");
  const [framework, setFramework] = useState("HAL");
  const [toolchain, setToolchain] = useState("ARM GCC");
  const [iocName, setIocName] = useState("");
  const [iocText, setIocText] = useState("");
  const [preview, setPreview] = useState<IocAnalysis | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [platforms, setPlatforms] = useState<PlatformCapability[]>([]);
  const [existingPath, setExistingPath] = useState("");
  const selectedAdapter = useMemo(() => platforms.find((p) => p.platform === platform), [platforms, platform]);

  useEffect(() => {
    if (modeLive !== "live") return;
    void listPlatforms().then(setPlatforms);
  }, [modeLive]);

  const onPickIoc = async (file: File | undefined) => {
    if (!file) return;
    const text = await file.text();
    setIocName(file.name);
    setIocText(text);
    setPreview(null);
    setErr(null);
    const r = await analyzeIoc(text, file.name);
    if (!r.available || !r.analysis) {
      setErr(r.reason ?? "Backend Not Implemented");
      return;
    }
    setPreview(r.analysis);
  };

  const analyzeOrImport = async (doImport: boolean) => {
    if (!iocText) {
      setErr("请选择 .ioc 文件");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      const r = doImport ? await importIoc(iocText, iocName) : await analyzeIoc(iocText, iocName);
      if (!r.available || !r.analysis) {
        setErr(r.reason ?? "Backend Not Implemented");
        return;
      }
      applyIocToHardware(r.analysis, setContext as (c: Record<string, unknown>) => void, setIoc);
      if (doImport && r.projectId) setProjectId(r.projectId);
      router.push("/ioc");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl p-6">
      <div className="text-[11px] text-muted-foreground">创建 STM32 项目</div>
      <h1 className="text-[18px] font-semibold">创建嵌入式工程</h1>
      <div className="mt-4 grid grid-cols-3 gap-2">
        {(
          [
            ["new", "新建工程"],
            ["ioc", "导入 CubeMX .ioc"],
            ["existing", "导入已有工程"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => {
              setMode(id);
              setErr(null);
            }}
            className={cn("rounded-sm border px-3 py-3 text-[12px]", mode === id ? "border-primary bg-accent" : "border-border")}
          >
            {label}
          </button>
        ))}
      </div>

      {mode === "ioc" && (
        <div className="mt-5 space-y-3">
          <label className="block text-[12px] text-muted-foreground">
            选择 .ioc 文件
            <input
              type="file"
              accept=".ioc"
              className="mt-1 block w-full text-[12px]"
              onChange={(e) => void onPickIoc(e.target.files?.[0])}
            />
          </label>
          {iocName && <div className="font-mono text-[12px]">{iocName}</div>}
          {preview && (
            <dl className="grid grid-cols-2 gap-2 rounded-md border border-border bg-panel p-3 text-[12px]">
              <div>MCU <span className="font-mono">{preview.mcu}</span></div>
              <div>Board <span className="font-mono">{preview.board ?? "—"}</span></div>
              <div>Clock <span className="font-mono">{preview.clock?.sysclkHz ? `${Math.round(preview.clock.sysclkHz / 1e6)} MHz` : "—"}</span></div>
              <div>HSE <span className="font-mono">{preview.clock?.hseHz ? `${Math.round(preview.clock.hseHz / 1e6)} MHz` : "—"}</span></div>
            </dl>
          )}
          {err && <CapabilityBanner reason={err} />}
          <div className="flex gap-2">
            <Button disabled={busy || !iocText} variant="outline" onClick={() => void analyzeOrImport(false)}>
              分析工程
            </Button>
            <Button disabled={busy || !iocText || modeLive !== "live"} onClick={() => void analyzeOrImport(true)}>
              导入并打开 IOC
            </Button>
          </div>
          {modeLive !== "live" && <p className="text-[11px] text-muted-foreground">导入需要 LIVE 后端。分析可在后端可用时执行。</p>}
        </div>
      )}

      {mode === "existing" && (
        <div className="mt-5 space-y-3">
          <p className="text-[12px] text-muted-foreground">输入后端主机可访问的工程目录绝对路径。导入前可先扫描，不会修改源目录。</p>
          <input className="w-full rounded-sm border border-border bg-background px-3 py-2 font-mono text-[12px]" value={existingPath} onChange={(e) => setExistingPath(e.target.value)} placeholder="C:\\firmware\\my-project" />
          <div className="flex gap-2">
            <Button variant="outline" disabled={!existingPath || busy || modeLive !== "live"} onClick={async () => { setBusy(true); setErr(null); const r = await scanExistingProject(existingPath); setErr(r.available ? `扫描完成：${String(r.platform ?? r.mcu ?? "已识别工程")}` : r.reason ?? "扫描失败"); setBusy(false); }}>扫描工程</Button>
            <Button disabled={!existingPath || busy || modeLive !== "live"} onClick={async () => { setBusy(true); setErr(null); const r = await importExistingProject(existingPath); if (r.available && r.id) { setProjectId(r.id); router.push("/agent"); } else setErr(r.reason ?? "导入失败"); setBusy(false); }}>导入已有工程</Button>
          </div>
          {err && <CapabilityBanner reason={err} />}
          {modeLive !== "live" && <p className="text-[11px] text-muted-foreground">导入需要 LIVE 后端。</p>}
        </div>
      )}

      {mode === "new" && (
        <>
          <p className="mt-4 text-[13px] text-muted-foreground">
            {step === 1 && "选择平台"}
            {step === 2 && "选择 MCU"}
            {step === 3 && "选择开发框架"}
            {step === 4 && "选择工具链"}
          </p>
          {step === 1 && (
            <div className="mt-4 grid grid-cols-3 gap-2">
              {(platforms.length ? platforms : [{ id: "stm32f103-hal", platform: "STM32", status: "ready" }, ...["ESP32", "8051", "AVR", "RP2040", "Linux"].map((p) => ({ id: p, platform: p, status: "unsupported" }))]).map((p) => (
                <button key={p.id} type="button" disabled={p.status === "unsupported"} title={p.status === "unsupported" ? "后端尚未注册该平台" : undefined} onClick={() => setPlatform(p.platform as PlatformId)} className={cn("rounded-sm border px-3 py-4", platform === p.platform ? "border-primary bg-accent" : "border-border", p.status === "unsupported" && "cursor-not-allowed opacity-45")}>
                  {p.platform}<span className="ml-1 text-[10px] text-muted-foreground">{p.status}</span>
                </button>
              ))}
            </div>
          )}
          {step === 2 && (
            <div className="mt-4 space-y-1">
              {mcuCatalog.map((m) => (
                <button key={m.id} type="button" onClick={() => setMcu(m.name)} className={cn("flex w-full justify-between rounded-sm border px-3 py-2", mcu === m.name ? "border-primary bg-accent" : "border-border")}>
                  <span className="font-mono">{m.name}</span>
                  <span className="text-[11px] text-muted-foreground">{m.core}</span>
                </button>
              ))}
            </div>
          )}
          {step === 3 && (
            <div className="mt-4 grid grid-cols-2 gap-2">
              {["HAL", "LL", "CMSIS", "Bare Metal"].map((f) => (
                <button key={f} type="button" onClick={() => setFramework(f)} className={cn("rounded-sm border px-3 py-3", framework === f ? "border-primary bg-accent" : "border-border")}>
                  {f === "Bare Metal" ? "裸机" : f}
                </button>
              ))}
            </div>
          )}
          {step === 4 && (
            <div className="mt-4 grid grid-cols-2 gap-2">
              {["ARM GCC", "Keil", "PlatformIO"].map((t) => (
                <button key={t} type="button" onClick={() => setToolchain(t)} className={cn("rounded-sm border px-3 py-3", toolchain === t ? "border-primary bg-accent" : "border-border")}>
                  {t}
                </button>
              ))}
            </div>
          )}
          <div className="mt-6 flex justify-between">
            <Button variant="outline" disabled={step === 1} onClick={() => setStep((s) => s - 1)}>
              上一步
            </Button>
            {step < 4 ? (
              <Button onClick={() => setStep((s) => s + 1)}>下一步</Button>
            ) : (
              <Button
                onClick={() => {
                  setContext({ platform, mcu, framework, buildTool: toolchain });
                  void start({ name: `${mcu} Project`, platform, mcu, framework, toolchain, board: selectedAdapter?.boards[0], adapterId: selectedAdapter?.id });
                  router.push("/agent");
                }}
              >
                创建并进入 Agent
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

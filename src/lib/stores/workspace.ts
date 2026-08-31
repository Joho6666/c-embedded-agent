"use client";

import { create } from "zustand";
import type { AgentMode, AgentStatus, AgentStep, PlanStep } from "@/types/agent";
import type { CodeDiff, SerialLine } from "@/types/debug";
import { GPIO_H_FIXED, initialFiles } from "@/lib/mock/files";
import { demoEvents, demoPlan, DEMO_PROMPT } from "@/lib/mock/demo";
import { latestBuild } from "@/lib/mock/build";
import { projects } from "@/lib/mock/projects";

export type BottomTab = "terminal" | "build" | "problems" | "serial" | "debug";
export type BuildPhase = "idle" | "error" | "success" | "flash";

interface WorkspaceState {
  projectId: string;
  agentStatus: AgentStatus;
  statusText: string;
  mode: AgentMode;
  prompt: string;
  platform: string;
  mcu: string;
  framework: string;
  rtos: string;
  buildTool: string;
  steps: AgentStep[];
  plan: PlanStep[];
  terminalLines: string[];
  serialLines: SerialLine[];
  files: Record<string, { path: string; language: string; content: string }>;
  activeFile: string;
  diffs: CodeDiff[];
  sidebarCollapsed: boolean;
  bottomOpen: boolean;
  bottomTab: BottomTab;
  commandOpen: boolean;
  buildPhase: BuildPhase;
  problemsActive: boolean;
  running: boolean;
  abort?: () => void;
  setPrompt: (v: string) => void;
  setMode: (m: AgentMode) => void;
  setSelectors: (
    p: Partial<Pick<WorkspaceState, "platform" | "mcu" | "framework" | "rtos" | "buildTool">>,
  ) => void;
  toggleSidebar: () => void;
  setBottomTab: (t: BottomTab) => void;
  toggleBottom: () => void;
  setCommandOpen: (v: boolean) => void;
  setActiveFile: (path: string) => void;
  acceptDiff: (path: string) => void;
  rejectDiff: (path: string) => void;
  acceptAll: () => void;
  appendTerminal: (lines: string[]) => void;
  runBuild: () => void;
  runFlash: () => void;
  stopAgent: () => void;
  startDemo: () => void;
}

const clonePlan = (): PlanStep[] => demoPlan.map((p) => ({ ...p, status: "pending" }));

export const useWorkspace = create<WorkspaceState>((set, get) => ({
  projectId: "p-led",
  agentStatus: "ready",
  statusText: "Agent Ready",
  mode: "auto",
  prompt: DEMO_PROMPT,
  platform: "STM32",
  mcu: "STM32F103C8T6",
  framework: "HAL",
  rtos: "None",
  buildTool: "ARM GCC",
  steps: [],
  plan: clonePlan(),
  terminalLines: ["$ ready", "C-Embedded Agent 工作台已就绪"],
  serialLines: [],
  files: { ...initialFiles },
  activeFile: "/Core/Src/main.c",
  diffs: [],
  sidebarCollapsed: false,
  bottomOpen: true,
  bottomTab: "terminal",
  commandOpen: false,
  buildPhase: "idle",
  problemsActive: false,
  running: false,

  setPrompt: (v) => set({ prompt: v }),
  setMode: (m) => set({ mode: m }),
  setSelectors: (p) => set(p),
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setBottomTab: (t) => set({ bottomTab: t, bottomOpen: true }),
  toggleBottom: () => set((s) => ({ bottomOpen: !s.bottomOpen })),
  setCommandOpen: (v) => set({ commandOpen: v }),
  setActiveFile: (path) => set({ activeFile: path }),

  acceptDiff: (path) =>
    set((s) => {
      const diff = s.diffs.find((d) => d.path === path);
      if (!diff) return s;
      return {
        files: {
          ...s.files,
          [path]: { ...(s.files[path] ?? { path, language: "c" }), content: diff.modified },
        },
        diffs: s.diffs.map((d) => (d.path === path ? { ...d, accepted: true } : d)),
      };
    }),
  rejectDiff: (path) =>
    set((s) => ({
      diffs: s.diffs.map((d) => (d.path === path ? { ...d, accepted: false } : d)),
    })),
  acceptAll: () =>
    set((s) => {
      const files = { ...s.files };
      for (const d of s.diffs) {
        files[d.path] = { ...(files[d.path] ?? { path: d.path, language: "c" }), content: d.modified };
      }
      return { files, diffs: s.diffs.map((d) => ({ ...d, accepted: true })) };
    }),
  appendTerminal: (lines) => set((s) => ({ terminalLines: [...s.terminalLines, ...lines] })),

  runBuild: () => {
    if (get().running) return;
    set({
      agentStatus: "working",
      statusText: "正在编译...",
      bottomTab: "build",
      bottomOpen: true,
      buildPhase: "idle",
    });
    get().appendTerminal(["$ make -j8", "[1/18] Building main.c"]);
    window.setTimeout(() => {
      get().appendTerminal([
        "[18/18] Linking stm32_led.elf",
        "Build successful",
        `FLASH   ${latestBuild.flashUsedKb * 1024} / ${latestBuild.flashTotalKb * 1024}`,
      ]);
      set({
        agentStatus: "ready",
        statusText: "Build Successful",
        buildPhase: "success",
        problemsActive: false,
      });
    }, 1400);
  },

  runFlash: () => {
    set({
      agentStatus: "working",
      statusText: "正在烧录...",
      bottomTab: "terminal",
      bottomOpen: true,
      buildPhase: "flash",
    });
    get().appendTerminal([
      "$ openocd -f interface/stlink.cfg -f target/stm32f1x.cfg",
      "Info : STLINK V2 detected",
    ]);
    window.setTimeout(() => {
      get().appendTerminal(["** Programming Finished **", "** Verify OK **"]);
      set({ agentStatus: "ready", statusText: "Flash 完成", buildPhase: "success" });
    }, 1200);
  },

  stopAgent: () => {
    get().abort?.();
    set({ running: false, agentStatus: "stopped", statusText: "已停止", abort: undefined });
  },

  startDemo: () => {
    get().abort?.();
    let cancelled = false;
    set({
      running: true,
      agentStatus: "working",
      statusText: "Agent Working",
      steps: [],
      plan: clonePlan(),
      serialLines: [],
      diffs: [],
      problemsActive: false,
      buildPhase: "idle",
      terminalLines: ["$ agent run --demo stm32-led"],
      files: { ...initialFiles },
      prompt: DEMO_PROMPT,
      abort: () => {
        cancelled = true;
      },
    });

    const run = async () => {
      for (const ev of demoEvents) {
        if (cancelled) return;
        await new Promise((r) => setTimeout(r, ev.delay));
        if (cancelled) return;
        set((s) => {
          const steps = [...s.steps];
          if (ev.step) {
            const idx = steps.findIndex((x) => x.id === ev.step!.id);
            if (idx >= 0) steps[idx] = ev.step;
            else steps.push(ev.step);
          }
          const plan = s.plan.map((p) =>
            ev.planId && p.id === ev.planId && ev.planStatus ? { ...p, status: ev.planStatus } : p,
          );
          const diffs = ev.showDiff
            ? [
                {
                  path: "/Core/Inc/gpio.h",
                  original: s.files["/Core/Inc/gpio.h"]?.content ?? "",
                  modified: GPIO_H_FIXED,
                  accepted: null,
                },
              ]
            : s.diffs;
          const files = ev.showDiff
            ? {
                ...s.files,
                "/Core/Inc/gpio.h": {
                  path: "/Core/Inc/gpio.h",
                  language: "c",
                  content: GPIO_H_FIXED,
                },
              }
            : s.files;
          return {
            statusText: ev.statusText,
            agentStatus: "working" as AgentStatus,
            steps,
            plan,
            terminalLines: ev.terminal ? [...s.terminalLines, ...ev.terminal] : s.terminalLines,
            serialLines: ev.serial ? [...s.serialLines, ...ev.serial] : s.serialLines,
            diffs,
            files,
            buildPhase: ev.buildPhase ?? s.buildPhase,
            problemsActive: ev.problemsActive ?? s.problemsActive,
            bottomTab: ev.serial ? "serial" : ev.buildPhase === "error" ? "problems" : s.bottomTab,
            bottomOpen: true,
            activeFile: ev.showDiff ? "/Core/Inc/gpio.h" : s.activeFile,
          };
        });
      }
      if (!cancelled) {
        set({ running: false, agentStatus: "ready", statusText: "Validation Passed" });
      }
    };
    void run();
  },
}));

export function currentProject() {
  const id = useWorkspace.getState().projectId;
  return projects.find((p) => p.id === id) ?? projects[0];
}

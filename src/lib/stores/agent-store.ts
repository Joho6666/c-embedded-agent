"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AgentMode, AgentStatus } from "@/types/agent";
import type { AgentApproval, AgentDiagnostic, AgentEvent } from "@/types/events";
import type { AgentRun } from "@/types/run";
import type { ValidationResult } from "@/types/validation";
import type { ApprovalDecision } from "@/lib/api/agent";
import { getAgentBackend } from "@/lib/api";
import { useEditor } from "./editor-store";
import { useTerminal } from "./terminal-store";
import { useWorkspaceUI } from "./workspace-store";
import { useHardware } from "./hardware-store";
import { DEMO_PROMPT } from "@/lib/mock/files";
import { useProject } from "./project-store";
import { createProject } from "@/lib/api/project";
import type { CreateProjectInput } from "@/types/platform";

interface AgentState {
  prompt: string;
  mode: AgentMode;
  status: AgentStatus;
  statusText: string;
  activeRun?: AgentRun;
  events: AgentEvent[];
  diagnostics: AgentDiagnostic[];
  validations: ValidationResult[];
  approval?: AgentApproval;
  liveRun: boolean;
  unsubscribe?: () => void;
  setPrompt: (v: string) => void;
  setMode: (m: AgentMode) => void;
  startGoldenPath: (project?: CreateProjectInput) => Promise<void>;
  startRun: (project?: CreateProjectInput) => Promise<void>;
  stopRun: () => Promise<void>;
  approve: (decision: ApprovalDecision, approvalId?: string) => Promise<void>;
}

function applyEvent(event: AgentEvent) {
  const terminal = useTerminal.getState();
  const ui = useWorkspaceUI.getState();
  const editor = useEditor.getState();

  if (event.tool?.command) {
    const toolchain = useHardware.getState().context.buildTool;
    const cmd =
      event.type === "compile" && toolchain === "Keil"
        ? "UV4.exe -b STM32_LED_Project.uvprojx"
        : event.tool.command;
    terminal.appendTerminal([`$ ${cmd}`]);
  }
  if (event.type === "terminal" && (event.content || event.output)) {
    const line = event.content || event.output || "";
    terminal.appendTerminal([line]);
    terminal.appendBuild([line]);
  }
  if (event.output && event.type !== "terminal") {
    terminal.appendTerminal([event.output]);
    if (event.type === "compile") terminal.appendBuild([event.output]);
  }
  if (event.type === "serial" && event.output) {
    const m = event.output.match(/\[(.+?)\]\s*(.*)/);
    terminal.appendSerial([{ ts: m?.[1] ?? "00:00:00", text: m?.[2] ?? event.output }]);
    ui.setBottomTab("serial");
  }
  if (event.type === "compile" && event.status === "failed") ui.setBottomTab("problems");
  if (event.type === "file_diff" && event.files?.[0] && (event.proposed || event.after)) {
    const p = event.files[0].startsWith("/") ? event.files[0] : `/${event.files[0]}`;
    const proposed = event.proposed ?? event.after ?? "";
    const original = event.original ?? event.before ?? "";
    if (event.status === "waiting_approval") {
      editor.addPatch({
        id: event.id,
        runId: event.runId,
        path: p,
        original,
        proposed,
        status: "pending",
        reason: event.description ?? event.title,
        createdAt: event.timestamp,
        approvalId: event.approvalId,
      });
      ui.setAgentView("code");
    } else if (event.status === "success") {
      editor.setContent(p, proposed);
      editor.saveFile(p);
    }
  }
  if (event.type === "file_write" && event.files?.length) {
    const first = event.files.find((f) => f.endsWith(".c") || f.endsWith(".h"));
    if (first) {
      const path = first.startsWith("/")
        ? first
        : first.includes("gpio.h")
          ? "/Core/Inc/gpio.h"
          : first.includes("gpio.c")
            ? "/Core/Src/gpio.c"
            : "/Core/Src/main.c";
      editor.openFile(path);
    }
  }
  if (event.type === "pin_conflict" && event.status === "waiting_approval") {
    useHardware.getState().setConflict({
      pin: "PA9",
      current: { pin: "PA9", function: "USART1_TX", peripheral: "USART1", source: "board" },
      requested: { pin: "PA9", function: "TIM1_CH2", peripheral: "TIM1", source: "agent" },
    });
  }
  if (event.type === "pin_conflict" && event.status !== "waiting_approval") {
    useHardware.getState().setConflict(undefined);
  }
}

export const useAgent = create<AgentState>()(
  persist(
    (set, get) => ({
      prompt: DEMO_PROMPT,
      mode: "auto",
      status: "ready",
      statusText: "Agent 就绪",
      events: [],
      diagnostics: [],
      validations: [],
      liveRun: false,

      setPrompt: (v) => set({ prompt: v }),
      setMode: (m) => set({ mode: m }),

      startGoldenPath: async (project) => {
        await get().startRun(project);
      },

      startRun: async (project) => {
        get().unsubscribe?.();
        const { useLive } = await import("./live-store");
        await useLive.getState().refresh();
        const live = useLive.getState().mode === "live";
        const backend = getAgentBackend();
        useEditor.getState().resetFiles();
        useTerminal.getState().reset();
        useHardware.getState().setConflict(undefined);
        let projectId = useProject.getState().projectId;
        if (live) {
          try {
            const { API_BASE } = await import("@/lib/api/client");
            const created = await createProject(project ?? {
              name: "STM32 LED",
              platform: "STM32",
              mcu: "STM32F103C8T6",
              framework: "HAL",
              toolchain: "ARM GCC",
              board: "Blue Pill",
              adapterId: "stm32f103-hal",
            });
            if (created.id) {
              projectId = created.id;
              useProject.getState().setProjectId(created.id);
              const names = (await fetch(`${API_BASE}/api/projects/${created.id}/files`).then((r) => r.json())) as string[];
              const wanted = names.filter((n) => n.endsWith(".c") || n.endsWith(".h") || n === "Makefile").slice(0, 12);
              const loaded: Record<string, { path: string; language: string; content: string }> = {};
              for (const n of wanted) {
                const f = (await fetch(`${API_BASE}/api/projects/${created.id}/file?path=${encodeURIComponent(n)}`).then((r) => r.json())) as {
                  path: string;
                  content: string;
                };
                const path = f.path.startsWith("/") ? f.path : `/${f.path.replace(/\\/g, "/")}`;
                loaded[path] = {
                  path,
                  language: path.endsWith(".h") || path.endsWith(".c") ? "c" : "plaintext",
                  content: f.content,
                };
              }
              if (Object.keys(loaded).length) useEditor.getState().loadWorkspace(loaded);
            }
          } catch {
            useTerminal.getState().appendTerminal(["创建工程失败，仍尝试运行"]);
          }
          useTerminal.getState().appendTerminal(["$ live mode: POST /api/runs"]);
        }
        const hw = useHardware.getState().context;
        const run = await backend.createRun({
          projectId,
          prompt: get().prompt || DEMO_PROMPT,
          mode: get().mode,
          goldenPath: !live,
          serialDevice: live && hw.serialPort ? hw.serialPort : undefined,
          baud: hw.serialBaud,
          expect: /hello/i.test(get().prompt) ? "Hello" : undefined,
        });
        const unsub = backend.subscribeEvents(run.id, (event) => {
          if (event.description !== "__run_end__" && event.type !== "run_stopped") applyEvent(event);
          set((s) => {
            if (event.type === "run_stopped") {
              return {
                status: "stopped" as const,
                statusText: "已停止",
                approval: undefined,
                liveRun: false,
                activeRun: s.activeRun ? { ...s.activeRun, status: "cancelled" } : s.activeRun,
              };
            }
            if (event.description === "__run_end__") {
              return {
                status: event.status === "success" ? "ready" : "stopped",
                statusText: event.title,
                approval: undefined,
                liveRun: false,
                activeRun: s.activeRun ? { ...s.activeRun, status: event.status === "success" ? "success" : "failed" } : s.activeRun,
              };
            }
            const events = [...s.events.filter((e) => e.id !== event.id), event];
            const rawPlan = (event as unknown as { plan?: AgentRun["plan"] }).plan;
            const planFromEvent = Array.isArray(rawPlan) ? rawPlan : undefined;
            const diagnostics = event.diagnostics?.length
              ? [...s.diagnostics.filter((d) => !event.diagnostics!.some((x) => x.id === d.id)), ...event.diagnostics]
              : s.diagnostics;
            const validations =
              event.type === "validation"
                ? [
                    ...s.validations,
                    (() => {
                      let parsed: { method?: string; expected?: string; observed?: string; status?: string } = {};
                      try {
                        parsed = JSON.parse(event.description || "{}") as typeof parsed;
                      } catch {
                        parsed = {};
                      }
                      const method = parsed.method || "static_source";
                      const status =
                        parsed.status === "pass" || event.status === "success"
                          ? ("pass" as const)
                          : parsed.status === "unknown"
                            ? ("unknown" as const)
                            : ("fail" as const);
                      return {
                        id: event.id,
                        runId: event.runId,
                        requirement: event.title,
                        method,
                        expected: parsed.expected || "static source checks",
                        observed: parsed.observed || event.description || "",
                        status,
                        evidence: event.description,
                        confidence: null,
                      };
                    })(),
                  ]
                : s.validations;
            const rail =
              event.requiresApproval &&
              event.status === "waiting_approval" &&
              event.type !== "file_diff";
            const approval = rail
              ? {
                  id: event.approvalId ?? event.id,
                  runId: event.runId,
                  eventId: event.id,
                  title: event.title,
                  summary: event.description ?? "",
                  steps:
                    event.type === "flash"
                      ? ["覆盖当前 firmware", "执行 Flash"]
                      : event.type === "pin_conflict"
                        ? ["保持 USART1_TX", "或改分配 TIM1_CH2"]
                        : ["确认继续"],
                  risk: event.risk ?? "medium",
                  status: "pending" as const,
                  createdAt: event.timestamp,
                }
              : event.approvalId && s.approval?.id === event.approvalId
                ? undefined
                : s.approval;
            const waiting = event.status === "waiting_approval";
            return {
              events,
              diagnostics,
              validations,
              approval,
              liveRun: true,
              status: waiting ? "waiting_approval" : "working",
              statusText: waiting ? "等待确认" : event.title,
              activeRun: {
                ...(s.activeRun ?? run),
                events,
                currentStep: event.title,
                status: waiting ? "waiting_approval" : "running",
                plan: planFromEvent ?? s.activeRun?.plan ?? run.plan,
              },
            };
          });
        });
        set({
          activeRun: run,
          events: [],
          diagnostics: [],
          validations: [],
          approval: undefined,
          liveRun: true,
          status: "working",
          statusText: "Agent 工作中",
          unsubscribe: unsub,
        });
      },

      stopRun: async () => {
        const run = get().activeRun;
        get().unsubscribe?.();
        if (run) await getAgentBackend().stopRun(run.id);
        set({ status: "stopped", statusText: "已停止", unsubscribe: undefined, liveRun: false, approval: undefined });
      },

      approve: async (decision, approvalId) => {
        const { activeRun, approval } = get();
        const id = approvalId ?? approval?.id;
        if (!activeRun || !id) return;
        await getAgentBackend().approveAction(activeRun.id, id, decision);
        if (decision === "rejected") {
          set({ approval: undefined });
        } else {
          set({ approval: undefined, status: "working", statusText: "Agent 工作中" });
        }
      },
    }),
    {
      name: "cea-agent",
      partialize: (s) => ({ prompt: s.prompt, mode: s.mode }),
    },
  ),
);

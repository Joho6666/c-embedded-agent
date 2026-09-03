import type { AgentBackend, ApprovalDecision, EventListener } from "@/lib/api/agent";
import type { AgentEvent } from "@/types/events";
import type { AgentMode } from "@/types/agent";
import type { AgentRun, CreateRunInput } from "@/types/run";
import { goldenPlan, goldenSteps } from "@/lib/mock/golden-path";

function nowIso() {
  return new Date().toISOString();
}

function uid(prefix: string) {
  return `${prefix}-${Math.random().toString(36).slice(2, 9)}`;
}

export function createMockAgentBackend(): AgentBackend {
  const runs = new Map<string, AgentRun>();
  const listeners = new Map<string, Set<EventListener>>();
  const cancelled = new Set<string>();
  const approvalWait = new Map<string, (d: ApprovalDecision) => void>();
  const alwaysAllow = new Set<string>();
  const modes = new Map<string, AgentMode>();

  function emit(runId: string, event: AgentEvent) {
    const run = runs.get(runId);
    if (run) {
      const idx = run.events.findIndex((e) => e.id === event.id);
      if (idx >= 0) run.events[idx] = event;
      else run.events.push(event);
      run.currentStep = event.title;
      if (event.artifacts?.length) run.artifacts.push(...event.artifacts);
    }
    listeners.get(runId)?.forEach((fn) => fn(event));
  }

  function finish(run: AgentRun, status: AgentRun["status"], error?: string) {
    run.status = status;
    run.finishedAt = nowIso();
    if (error) run.error = error;
    run.tokenUsage = { input: 4200, output: 1800 };
    emit(run.id, {
      id: uid("ev"),
      runId: run.id,
      type: status === "success" ? "plan" : "error",
      status: status === "success" ? "success" : "failed",
      title: status === "success" ? "运行完成" : (error ?? "已停止"),
      description: "__run_end__",
      timestamp: nowIso(),
    });
  }

  async function play(runId: string) {
    const run = runs.get(runId);
    if (!run) return;
    run.status = "planning";
    run.startedAt = nowIso();
    const mode = modes.get(runId) ?? "auto";

    for (const step of goldenSteps) {
      if (cancelled.has(runId)) {
        finish(run, "cancelled");
        return;
      }
      await new Promise((r) => setTimeout(r, step.delay));
      if (cancelled.has(runId)) return;

      const event: AgentEvent = {
        ...step.event,
        id: uid("ev"),
        runId,
        timestamp: nowIso(),
      };
      if (step.planId) {
        run.plan = run.plan.map((p) =>
          p.id === step.planId && step.planStatus ? { ...p, status: step.planStatus } : p,
        );
      }

      const needsWait = Boolean(event.requiresApproval || step.waitApproval);
      const skipWait = needsWait && event.type === "flash" && alwaysAllow.has("flash");

      if (needsWait && !skipWait) {
        const approvalId = uid("ap");
        event.approvalId = approvalId;
        event.status = "waiting_approval";
        event.requiresApproval = true;
        run.status = "waiting_approval";
        emit(runId, event);
        const decision = await new Promise<ApprovalDecision>((resolve) => {
          approvalWait.set(approvalId, resolve);
        });
        approvalWait.delete(approvalId);

        if (decision === "always" && event.type === "flash") alwaysAllow.add("flash");

        if (decision === "rejected") {
          event.status = "cancelled";
          if (event.type === "pin_conflict") {
            run.status = "running";
            run.plan = run.plan.map((p) => (p.id === "p4" ? { ...p, status: "pending" } : p));
            emit(runId, event);
            continue;
          }
          if (event.type === "file_diff") {
            run.plan = run.plan.map((p) => (p.id === "p5" ? { ...p, status: "failed" } : p));
            finish(run, "failed", "用户拒绝代码修改");
            emit(runId, event);
            return;
          }
          finish(run, "failed", "用户拒绝操作");
          emit(runId, event);
          return;
        }

        event.status = "success";
        run.status = "running";
        emit(runId, event);

        if (mode === "code" && event.type === "file_diff") {
          continue;
        }
        continue;
      }

      if (skipWait) {
        event.status = "success";
        event.requiresApproval = false;
      }

      run.status = "running";
      emit(runId, event);

      if (mode === "plan" && step.planId === "p1" && step.planStatus === "success") {
        finish(run, "success");
        return;
      }
      if (mode === "code" && event.type === "compile" && event.status === "success") {
        finish(run, "success");
        return;
      }
    }
    if (!cancelled.has(runId)) {
      finish(run, "success");
    }
  }

  return {
    async createRun(input: CreateRunInput) {
      const id = uid("run");
      const run: AgentRun = {
        id,
        projectId: input.projectId,
        prompt: input.prompt,
        mode: input.mode,
        status: "queued",
        createdAt: nowIso(),
        events: [],
        artifacts: [],
        plan: goldenPlan.map((p) => ({ ...p, status: "pending" })),
      };
      runs.set(id, run);
      modes.set(id, input.mode);
      void play(id);
      return run;
    },
    async stopRun(runId: string) {
      cancelled.add(runId);
      const run = runs.get(runId);
      if (run) finish(run, "cancelled");
      for (const [id, resolve] of approvalWait) {
        resolve("rejected");
        approvalWait.delete(id);
      }
    },
    async approveAction(_runId: string, approvalId: string, decision: ApprovalDecision) {
      approvalWait.get(approvalId)?.(decision);
    },
    async listRuns() {
      return [...runs.values()];
    },
    async getRun(id: string) {
      return runs.get(id);
    },
    subscribeEvents(runId: string, onEvent: EventListener) {
      const set = listeners.get(runId) ?? new Set<EventListener>();
      set.add(onEvent);
      listeners.set(runId, set);
      return () => {
        set.delete(onEvent);
      };
    },
  };
}

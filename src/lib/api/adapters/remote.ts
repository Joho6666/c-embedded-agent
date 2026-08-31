import { apiFetch, API_BASE } from "@/lib/api/client";
import { API_ROUTES } from "@/lib/api/contract";
import type { AgentBackend, ApprovalDecision, EventListener } from "@/lib/api/agent";
import type { AgentEvent } from "@/types/events";
import type { AgentRun, CreateRunInput } from "@/types/run";

export function createRemoteAgentBackend(): AgentBackend {
  return {
    async createRun(input: CreateRunInput) {
      const created = await apiFetch<{ id: string }>(API_ROUTES.runs, {
        method: "POST",
        body: JSON.stringify({
          prompt: input.prompt,
          projectId: input.projectId,
          mode: input.mode,
        }),
      });
      const run: AgentRun = {
        id: created.id,
        projectId: input.projectId,
        prompt: input.prompt,
        mode: input.mode,
        status: "running",
        createdAt: new Date().toISOString(),
        events: [],
        artifacts: [],
        plan: [],
      };
      return run;
    },
    stopRun: (id) => apiFetch(API_ROUTES.stop(id), { method: "POST" }),
    approveAction: (runId, approvalId, decision: ApprovalDecision) =>
      apiFetch(API_ROUTES.approve(runId), {
        method: "POST",
        body: JSON.stringify({ approvalId, decision }),
      }),
    listRuns: async () => [],
    getRun: (id) => apiFetch<AgentRun>(API_ROUTES.run(id)),
    subscribeEvents(runId: string, onEvent: EventListener) {
      const es = new EventSource(`${API_BASE}${API_ROUTES.events(runId)}`);
      const handler = (msg: MessageEvent<string>) => {
        try {
          onEvent(JSON.parse(msg.data) as AgentEvent);
        } catch {
          /* ignore */
        }
      };
      es.addEventListener("agent_event", handler);
      es.onmessage = handler;
      return () => es.close();
    },
  };
}

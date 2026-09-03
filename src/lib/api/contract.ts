/**
 * SSE / REST contract for FastAPI backend.
 *
 * POST /api/runs
 * GET  /api/runs/:id
 * GET  /api/runs
 * POST /api/runs/:id/stop
 * POST /api/runs/:id/approve  { approvalId, decision: "approved" | "rejected" | "once" | "always" }
 * GET  /api/runs/:id/events   text/event-stream
 *
 * SSE:
 * event: agent_event
 * data: { AgentEvent JSON }
 *
 * Serial / Debug later: WebSocket /ws/serial /ws/debug
 */
export const API_ROUTES = {
  runs: "/api/runs",
  run: (id: string) => `/api/runs/${id}`,
  stop: (id: string) => `/api/runs/${id}/stop`,
  approve: (id: string) => `/api/runs/${id}/approve`,
  events: (id: string) => `/api/runs/${id}/events`,
  importIoc: "/api/projects/import-ioc",
  analyzeIoc: "/api/projects/analyze-ioc",
  projectIoc: (id: string) => `/api/projects/${id}/ioc`,
  hardwareRun: "/api/hardware/run",
  autoDebug: "/api/hardware/auto-debug",
  skills: "/api/skills",
  skill: (id: string) => `/api/skills/${id}`,
  errorMemories: "/api/memory/errors",
  errorMemory: (id: string) => `/api/memory/errors/${id}`,
  validation: "/api/validation",
  benchmark: "/api/benchmark",
} as const;

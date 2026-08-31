import { createMockAgentBackend } from "./adapters/mock";
import { createRemoteAgentBackend } from "./adapters/remote";
import type { AgentBackend } from "./agent";
import { useLive } from "@/lib/stores/live-store";

export function getAgentBackend(): AgentBackend {
  if (useLive.getState().mode === "live") {
    return createRemoteAgentBackend();
  }
  return createMockAgentBackend();
}

export * from "./client";
export * from "./contract";
export * from "./agent";

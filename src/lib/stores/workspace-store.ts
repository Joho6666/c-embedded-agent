"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type BottomTab = "terminal" | "build" | "problems" | "serial" | "debug";
export type AgentView = "timeline" | "code";

interface WorkspaceUIState {
  sidebarCollapsed: boolean;
  bottomOpen: boolean;
  bottomTab: BottomTab;
  commandOpen: boolean;
  agentView: AgentView;
  knowledgeId?: string;
  toggleSidebar: () => void;
  setBottomTab: (t: BottomTab) => void;
  toggleBottom: () => void;
  setCommandOpen: (v: boolean) => void;
  setAgentView: (v: AgentView) => void;
  setKnowledgeId: (id?: string) => void;
}

export const useWorkspaceUI = create<WorkspaceUIState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      bottomOpen: true,
      bottomTab: "terminal",
      commandOpen: false,
      agentView: "timeline",
      knowledgeId: undefined,
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setBottomTab: (t) => set({ bottomTab: t, bottomOpen: true }),
      toggleBottom: () => set((s) => ({ bottomOpen: !s.bottomOpen })),
      setCommandOpen: (v) => set({ commandOpen: v }),
      setAgentView: (v) => set({ agentView: v }),
      setKnowledgeId: (id) => set({ knowledgeId: id }),
    }),
    { name: "cea-ui", partialize: (s) => ({ sidebarCollapsed: s.sidebarCollapsed, bottomTab: s.bottomTab, agentView: s.agentView }) },
  ),
);

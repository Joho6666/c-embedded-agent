"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type BottomTab = "problems" | "output" | "terminal" | "serial" | "debug" | "build";
export type AgentView = "timeline" | "code";
export type ActivityId = "explorer" | "agent" | "search" | "build" | "debug" | "hardware" | "problems";
export type AgentPanelTab = "conversation" | "plan" | "hardware" | "knowledge";

interface WorkspaceUIState {
  sidebarCollapsed: boolean;
  bottomOpen: boolean;
  bottomTab: BottomTab;
  commandOpen: boolean;
  agentView: AgentView;
  activity: ActivityId;
  agentPanelTab: AgentPanelTab;
  knowledgeId?: string;
  toggleSidebar: () => void;
  setBottomTab: (t: BottomTab) => void;
  toggleBottom: () => void;
  setCommandOpen: (v: boolean) => void;
  setAgentView: (v: AgentView) => void;
  setActivity: (v: ActivityId) => void;
  setAgentPanelTab: (v: AgentPanelTab) => void;
  setKnowledgeId: (id?: string) => void;
}

export const useWorkspaceUI = create<WorkspaceUIState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      bottomOpen: true,
      bottomTab: "terminal",
      commandOpen: false,
      agentView: "code",
      activity: "explorer",
      agentPanelTab: "plan",
      knowledgeId: undefined,
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setBottomTab: (t) => set({ bottomTab: t, bottomOpen: true }),
      toggleBottom: () => set((s) => ({ bottomOpen: !s.bottomOpen })),
      setCommandOpen: (v) => set({ commandOpen: v }),
      setAgentView: (v) => set({ agentView: v }),
      setActivity: (v) => set({ activity: v }),
      setAgentPanelTab: (v) => set({ agentPanelTab: v }),
      setKnowledgeId: (id) => set({ knowledgeId: id }),
    }),
    {
      name: "cea-ui",
      partialize: (s) => ({
        sidebarCollapsed: s.sidebarCollapsed,
        bottomTab: s.bottomTab,
        agentView: s.agentView,
        activity: s.activity,
      }),
    },
  ),
);

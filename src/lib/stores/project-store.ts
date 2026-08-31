"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { projects } from "@/lib/mock/projects";
import type { Project } from "@/types/project";

interface ProjectState {
  projectId: string;
  setProjectId: (id: string) => void;
}

export const useProject = create<ProjectState>()(
  persist(
    (set) => ({
      projectId: "p-led",
      setProjectId: (id) => set({ projectId: id }),
    }),
    { name: "cea-project" },
  ),
);

export function currentProject(): Project {
  const id = useProject.getState().projectId;
  return projects.find((p) => p.id === id) ?? projects[0];
}

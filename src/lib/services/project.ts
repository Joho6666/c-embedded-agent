import { sleep } from "@/lib/utils";
import { projects } from "@/lib/mock/projects";
import type { CreateProjectDraft, Project } from "@/types/project";

export async function listProjects(): Promise<Project[]> {
  await sleep(80);
  return projects;
}

export async function getProject(id: string): Promise<Project | undefined> {
  await sleep(40);
  return projects.find((p) => p.id === id);
}

export async function createProject(draft: CreateProjectDraft): Promise<Project> {
  await sleep(120);
  return {
    id: `p-${Date.now()}`,
    name: draft.name || `${draft.mcu}_Project`,
    slug: (draft.name || draft.mcu).toLowerCase().replace(/\s+/g, "-"),
    description: "新建工程",
    mcu: draft.mcu,
    platform: draft.platform || "STM32",
    framework: draft.framework,
    compiler: draft.toolchain,
    rtos: "None",
    gitBranch: "main",
    createdAt: new Date().toISOString().slice(0, 16).replace("T", " "),
    updatedAt: new Date().toISOString().slice(0, 16).replace("T", " "),
    buildStatus: "idle",
  };
}

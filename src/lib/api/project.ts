import { apiFetch } from "./client";
import type { Project } from "@/types/project";
import { useLive } from "@/lib/stores/live-store";

interface BackendProject {
  id: string;
  name?: string;
  mcu?: string;
  platform?: string;
  framework?: string;
  toolchain?: string;
  board?: string;
}

export function mapBackendProject(p: BackendProject): Project {
  return {
    id: p.id,
    name: p.name ?? p.id,
    slug: p.id,
    description: p.board ?? "",
    mcu: p.mcu ?? "",
    platform: (p.platform as Project["platform"]) || "STM32",
    framework: p.framework ?? "",
    compiler: p.toolchain ?? "",
    rtos: "",
    gitBranch: "",
    createdAt: "",
    updatedAt: "",
    buildStatus: "idle",
  };
}

export async function listProjects(): Promise<Project[]> {
  if (useLive.getState().mode !== "live") {
    return [];
  }
  try {
    const rows = await apiFetch<BackendProject[]>("/api/projects");
    return Array.isArray(rows) ? rows.map(mapBackendProject) : [];
  } catch {
    return [];
  }
}

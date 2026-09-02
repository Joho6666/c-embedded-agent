import { apiFetch } from "./client";
import type { Project } from "@/types/project";
import { useLive } from "@/lib/stores/live-store";
import { normalizePlatformId } from "@/lib/platform";

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
  const platformId = normalizePlatformId(p.platform);
  return {
    id: p.id,
    name: p.name ?? p.id,
    slug: p.id,
    description: p.board ?? "",
    mcu: p.mcu ?? "",
    platform: (p.platform as Project["platform"]) || "STM32",
    platformId,
    board: p.board,
    workspacePath: p.id,
    lastOpened: undefined,
    framework: p.framework ?? "",
    compiler: p.toolchain ?? "",
    rtos: "",
    gitBranch: "main",
    createdAt: "",
    updatedAt: "",
    buildStatus: "idle",
  };
}

export async function createRemoteProject(input: {
  name: string;
  mcu: string;
  framework: string;
}): Promise<Project | null> {
  if (useLive.getState().mode !== "live") return null;
  try {
    const row = await apiFetch<BackendProject>("/api/projects", {
      method: "POST",
      body: JSON.stringify(input),
    });
    return mapBackendProject(row);
  } catch {
    return null;
  }
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

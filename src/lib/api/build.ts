import { sleep } from "@/lib/utils";
import { latestBuild, problems } from "@/lib/mock/build";
import { API_BASE } from "./client";

export async function getLatestBuild() {
  await sleep(20);
  return latestBuild;
}

export async function listProblems() {
  await sleep(20);
  return problems;
}

export async function compileProject(projectId: string): Promise<{ success: boolean; combined?: string; error?: string; exit_code?: number }> {
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/build`, { method: "POST" });
  const data = (await res.json().catch(() => ({}))) as { success?: boolean; combined?: string; error?: string; exit_code?: number };
  if (!res.ok && data.success == null) {
    return { success: false, error: `${res.status} /api/projects/${projectId}/build` };
  }
  return { success: Boolean(data.success), combined: data.combined, error: data.error, exit_code: data.exit_code };
}

export async function flashProject(projectId: string): Promise<{ success: boolean; error?: string; output?: string; status?: string }> {
  const res = await fetch(`${API_BASE}/api/projects/${encodeURIComponent(projectId)}/flash`, { method: "POST" });
  const data = (await res.json().catch(() => ({}))) as { success?: boolean; error?: string; output?: string; status?: string };
  return {
    ...data,
    success: res.ok && (data.success === true || data.status === "PASS"),
    error: data.error ?? (!res.ok ? `${res.status} flash request failed` : undefined),
  };
}

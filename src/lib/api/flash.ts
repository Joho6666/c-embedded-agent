import { API_BASE } from "./client";

export async function flashProject(projectId: string): Promise<{ ok: boolean; error?: string; log?: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}/flash`, { method: "POST" });
    const data = (await res.json().catch(() => ({}))) as { ok?: boolean; error?: string; log?: string; detail?: string };
    if (!res.ok) {
      return { ok: false, error: data.detail || data.error || `${res.status} flash` };
    }
    return { ok: true, log: data.log };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Backend capability unavailable" };
  }
}

import { API_BASE, apiFetch } from "./client";
import { BackendUnavailableError } from "./capability";
import type { IocAnalysis, IocImportResult } from "@/types/ioc";

export async function analyzeIoc(content: string, filename: string): Promise<IocImportResult> {
  try {
    return await apiFetch<IocImportResult>("/api/projects/analyze-ioc", {
      method: "POST",
      body: JSON.stringify({ content, filename }),
    });
  } catch (e) {
    return { available: false, reason: e instanceof Error ? e.message : "Backend Not Implemented" };
  }
}

export async function importIoc(content: string, filename: string, name?: string): Promise<IocImportResult> {
  try {
    const res = await fetch(`${API_BASE}/api/projects/import-ioc`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, filename, name: name ?? filename.replace(/\.ioc$/i, "") }),
    });
    if (res.status === 404 || res.status === 501) {
      throw new BackendUnavailableError(res.status, "/api/projects/import-ioc");
    }
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new BackendUnavailableError(res.status, "/api/projects/import-ioc", text || `${res.status} /api/projects/import-ioc`);
    }
    const data = (await res.json()) as IocImportResult;
    return { ...data, available: data.available !== false };
  } catch (e) {
    if (e instanceof BackendUnavailableError) {
      return { available: false, reason: e.message };
    }
    return { available: false, reason: e instanceof Error ? e.message : "Backend capability unavailable" };
  }
}

export async function getProjectIoc(projectId: string): Promise<IocImportResult> {
  try {
    const analysis = await apiFetch<IocAnalysis>(`/api/projects/${projectId}/ioc`);
    return { available: true, projectId, analysis };
  } catch (e) {
    return { available: false, reason: e instanceof Error ? e.message : "Backend capability unavailable" };
  }
}

export async function importExistingProject(): Promise<IocImportResult> {
  return { available: false, reason: "Backend Not Implemented" };
}

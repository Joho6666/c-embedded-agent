import { apiFetch } from "./client";
import type { ErrorMemoryEntry, ErrorMemoryTag } from "@/types/memory";

export interface ErrorMemoryListResult {
  available: boolean;
  reason?: string;
  items: ErrorMemoryEntry[];
}

export async function listErrorMemories(q?: string, tag?: ErrorMemoryTag | "all"): Promise<ErrorMemoryListResult> {
  try {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (tag && tag !== "all") params.set("tag", tag);
    const qs = params.toString();
    const items = await apiFetch<ErrorMemoryEntry[]>(`/api/memory/errors${qs ? `?${qs}` : ""}`);
    return { available: true, items: Array.isArray(items) ? items : [] };
  } catch (e) {
    return {
      available: false,
      reason: e instanceof Error && /404/.test(e.message) ? "Backend Not Implemented" : "Backend capability unavailable",
      items: [],
    };
  }
}

export async function searchErrorMemories(q: string): Promise<ErrorMemoryListResult> {
  return listErrorMemories(q);
}

export async function getErrorMemory(id: string): Promise<{ available: boolean; reason?: string; item?: ErrorMemoryEntry }> {
  try {
    const item = await apiFetch<ErrorMemoryEntry>(`/api/memory/errors/${id}`);
    return { available: true, item };
  } catch (e) {
    return {
      available: false,
      reason: e instanceof Error && /404/.test(e.message) ? "Backend Not Implemented" : "Backend capability unavailable",
    };
  }
}

import { apiFetch } from "./client";
import type { EmbeddedSkill } from "@/types/skill";

export interface SkillsListResult {
  available: boolean;
  reason?: string;
  skills: EmbeddedSkill[];
}

export async function listSkills(): Promise<SkillsListResult> {
  try {
    const skills = await apiFetch<EmbeddedSkill[]>("/api/skills");
    return { available: true, skills: Array.isArray(skills) ? skills : [] };
  } catch (e) {
    return {
      available: false,
      reason: e instanceof Error && /404/.test(e.message) ? "Backend Not Implemented" : "Backend capability unavailable",
      skills: [],
    };
  }
}

export async function getSkill(id: string): Promise<{ available: boolean; reason?: string; skill?: EmbeddedSkill }> {
  try {
    const skill = await apiFetch<EmbeddedSkill>(`/api/skills/${id}`);
    return { available: true, skill };
  } catch (e) {
    return {
      available: false,
      reason: e instanceof Error && /404/.test(e.message) ? "Backend Not Implemented" : "Backend capability unavailable",
    };
  }
}

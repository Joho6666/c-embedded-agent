import { sleep } from "@/lib/utils";
import { projects } from "@/lib/mock/projects";
import type { Project } from "@/types/project";

export async function listProjects(): Promise<Project[]> {
  await sleep(40);
  return projects;
}

import { sleep } from "@/lib/utils";
import { latestBuild, problems } from "@/lib/mock/build";
import type { BuildResult, Problem } from "@/types/build";

export async function getLatestBuild(): Promise<BuildResult> {
  await sleep(50);
  return latestBuild;
}

export async function listProblems(): Promise<Problem[]> {
  await sleep(40);
  return problems;
}

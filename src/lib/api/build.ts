import { sleep } from "@/lib/utils";
import { latestBuild, problems } from "@/lib/mock/build";

export async function getLatestBuild() {
  await sleep(20);
  return latestBuild;
}

export async function listProblems() {
  await sleep(20);
  return problems;
}

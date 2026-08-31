import { sleep } from "@/lib/utils";
import { tools } from "@/lib/mock/tools";
import type { ToolItem } from "@/types/tools";

export async function listTools(): Promise<ToolItem[]> {
  await sleep(50);
  return tools;
}

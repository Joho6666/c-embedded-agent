import { sleep } from "@/lib/utils";
import { callStack, registers, watches } from "@/lib/mock/build";

export async function getDebugSnapshot() {
  await sleep(20);
  return { registers, callStack, watches };
}

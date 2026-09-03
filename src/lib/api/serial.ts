import { sleep } from "@/lib/utils";
import { serialLog } from "@/lib/mock/build";

export async function getSerialLog() {
  await sleep(20);
  return serialLog;
}

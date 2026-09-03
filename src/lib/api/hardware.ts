import { sleep } from "@/lib/utils";
import { currentMcu, defaultHardware, pinMap } from "@/lib/mock/hardware";

export async function getHardwareContext() {
  await sleep(20);
  return defaultHardware;
}

export async function getCurrentMcu() {
  await sleep(20);
  return currentMcu;
}

export async function getPinMap() {
  await sleep(20);
  return pinMap;
}

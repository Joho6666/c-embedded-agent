import { sleep } from "@/lib/utils";
import { currentMcu, mcuCatalog, pinMap } from "@/lib/mock/mcu";
import type { McuInfo, PinConfig } from "@/types/mcu";

export async function getCurrentMcu(): Promise<McuInfo> {
  await sleep(40);
  return currentMcu;
}

export async function searchMcu(q: string): Promise<McuInfo[]> {
  await sleep(60);
  const s = q.trim().toLowerCase();
  if (!s) return mcuCatalog;
  return mcuCatalog.filter(
    (m) => m.name.toLowerCase().includes(s) || m.family.toLowerCase().includes(s),
  );
}

export async function getPinMap(): Promise<PinConfig[]> {
  await sleep(40);
  return pinMap;
}

import { apiFetch } from "./client";
import type { PlatformCapability } from "@/types/platform";

const unsupportedFallback: PlatformCapability[] = [
  { id: "stm32f103-hal", name: "STM32F103 HAL", platform: "STM32", status: "ready", mcus: ["STM32F103C8T6"], boards: ["bluepill_f103c8"], frameworks: ["HAL"], toolchains: ["ARM_GCC"], capabilities: ["create", "build", "flash"] },
  ...["ESP32", "8051", "AVR", "RP2040", "Linux"].map((platform) => ({ id: platform.toLowerCase(), name: platform, platform, status: "unsupported" as const, mcus: [], boards: [], frameworks: [], toolchains: [], capabilities: [], reason: "Backend adapter is not registered" })),
];

export async function listPlatforms(): Promise<PlatformCapability[]> {
  try {
    const data = await apiFetch<PlatformCapability[]>("/api/platforms", { cache: "no-store" });
    return Array.isArray(data) && data.length ? data : unsupportedFallback;
  } catch {
    return unsupportedFallback;
  }
}

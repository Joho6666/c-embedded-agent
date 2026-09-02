import { apiFetch } from "./client";
import { useLive } from "@/lib/stores/live-store";
import type { InstallStatus } from "@/types/status";

export interface EnvironmentItem {
  id: string;
  label: string;
  status: InstallStatus;
  version?: string | null;
  path?: string | null;
}

export interface EnvironmentPayload {
  os: string;
  items: EnvironmentItem[];
}

const UNKNOWN_ITEMS: EnvironmentItem[] = [
  "OS",
  "GCC",
  "Clang",
  "ARM GCC",
  "CMake",
  "Python",
  "Git",
  "STM32CubeMX",
  "OpenOCD",
  "ESP-IDF",
  "SDCC",
  "Keil",
].map((label) => ({
  id: label.toLowerCase().replace(/\s+/g, "-"),
  label,
  status: "unknown",
}));

export async function getEnvironment(): Promise<EnvironmentPayload> {
  if (useLive.getState().mode !== "live") {
    return { os: "unknown", items: UNKNOWN_ITEMS };
  }
  try {
    return await apiFetch<EnvironmentPayload>("/api/environment");
  } catch {
    return { os: "unknown", items: UNKNOWN_ITEMS.map((i) => ({ ...i, status: "unknown" })) };
  }
}

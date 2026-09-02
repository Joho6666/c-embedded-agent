import { apiFetch } from "./client";
import { useLive } from "@/lib/stores/live-store";
import type { DevicePresence } from "@/types/status";

export interface DeviceItem {
  id: string;
  label: string;
  presence: DevicePresence;
  detail?: string;
  installed?: boolean;
}

export interface DevicesPayload {
  probes: DeviceItem[];
  ports: DeviceItem[];
}

const UNKNOWN: DevicesPayload = {
  probes: [
    { id: "stlink", label: "ST-LINK V2", presence: "unknown", detail: "Probe status unknown" },
    { id: "cmsis-dap", label: "CMSIS-DAP", presence: "not_detected", detail: "Not Detected" },
  ],
  ports: [{ id: "serial", label: "Serial", presence: "unknown", detail: "Probe status unknown" }],
};

export async function getDevices(): Promise<DevicesPayload> {
  if (useLive.getState().mode !== "live") {
    return UNKNOWN;
  }
  try {
    return await apiFetch<DevicesPayload>("/api/devices");
  } catch {
    return UNKNOWN;
  }
}

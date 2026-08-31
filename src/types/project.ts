export type BuildStatusKind =
  | "passed"
  | "warning"
  | "failed"
  | "idle"
  | "running";

export type PlatformId =
  | "STM32"
  | "ESP32"
  | "8051"
  | "AVR"
  | "RP2040"
  | "Linux";

export interface Project {
  id: string;
  name: string;
  slug: string;
  description: string;
  mcu: string;
  platform: PlatformId;
  framework: string;
  compiler: string;
  rtos: string;
  gitBranch: string;
  createdAt: string;
  updatedAt: string;
  buildStatus: BuildStatusKind;
  warningCount?: number;
}

export interface CreateProjectDraft {
  platform: PlatformId | "";
  mcu: string;
  framework: string;
  toolchain: string;
  name: string;
}

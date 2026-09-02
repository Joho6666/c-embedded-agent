import type { PlatformId as CatalogPlatformId } from "./platform";

export type BuildStatusKind = "passed" | "warning" | "failed" | "idle" | "running";
/** Legacy display ids kept for existing mock rows. Prefer CatalogPlatformId. */
export type PlatformId = "STM32" | "ESP32" | "8051" | "AVR" | "RP2040" | "Linux" | CatalogPlatformId;

export interface Project {
  id: string;
  name: string;
  slug: string;
  description: string;
  mcu: string;
  platform: PlatformId;
  platformId?: CatalogPlatformId;
  board?: string;
  workspacePath?: string;
  lastOpened?: string;
  framework: string;
  compiler: string;
  rtos: string;
  gitBranch: string;
  createdAt: string;
  updatedAt: string;
  buildStatus: BuildStatusKind;
  warningCount?: number;
  previewOnly?: boolean;
}

export interface CreateProjectDraft {
  platform: PlatformId | CatalogPlatformId | "";
  mcu: string;
  framework: string;
  toolchain: string;
  name: string;
  board?: string;
  description?: string;
}

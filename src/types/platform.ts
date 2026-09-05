export type PlatformStatus = "ready" | "experimental" | "unsupported";

export interface PlatformCapability {
  id: string;
  name: string;
  platform: string;
  status: PlatformStatus;
  description?: string;
  mcus: string[];
  boards: string[];
  frameworks: string[];
  toolchains: string[];
  capabilities: string[];
  reason?: string;
}

export interface CreateProjectInput {
  name: string;
  platform: string;
  mcu: string;
  framework: string;
  toolchain?: string;
  board?: string;
  adapterId?: string;
}

export interface CreatedProject {
  id: string;
  adapterId?: string;
  capabilities?: string[];
}

import type { SupportStatus } from "./status";

export type PlatformId = "stm32" | "esp32" | "c51" | "rp2040" | "host-c";

export type ToolbarActionId =
  | "build"
  | "run"
  | "flash"
  | "debug"
  | "serial"
  | "validate"
  | "test"
  | "analyze"
  | "monitor"
  | "hex"
  | "stop";

export interface NamedOption {
  id: string;
  label: string;
  status?: SupportStatus;
}

export interface BoardDefinition extends NamedOption {
  mcu: string;
  architecture: string;
  clock: string;
  flashKb: number;
  ramKb: number;
  package?: string;
}

export interface PlatformDefinition {
  id: PlatformId;
  label: string;
  architecture: string;
  supported: boolean;
  status: SupportStatus;
  statusNote: string;
  frameworks: NamedOption[];
  toolchains: NamedOption[];
  boards: BoardDefinition[];
  flashAdapters: NamedOption[];
  debugAdapters: NamedOption[];
  serialCapabilities: boolean;
  skills: string[];
  toolbarActions: ToolbarActionId[];
  defaultMcu: string;
  defaultBoard: string;
  defaultFramework: string;
  defaultToolchain: string;
}

export const ALL_SKILLS = [
  "GPIO",
  "UART",
  "PWM",
  "TIMER",
  "ADC",
  "DMA",
  "I2C",
  "SPI",
  "CAN",
  "RTC",
  "WDT",
  "Wi-Fi",
  "BLE",
  "FreeRTOS",
] as const;

export type SkillId = (typeof ALL_SKILLS)[number];

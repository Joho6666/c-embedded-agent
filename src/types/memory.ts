export type ErrorMemoryTag =
  | "Compiler"
  | "Linker"
  | "HAL"
  | "GPIO"
  | "Clock"
  | "UART"
  | "DMA"
  | "TIM"
  | "ADC";

export interface ErrorMemoryEntry {
  id: string;
  pattern: string;
  mcu: string;
  family?: string;
  framework?: string;
  tag: ErrorMemoryTag;
  rootCause: string;
  fix: string;
  strategy?: string[];
  files: string[];
  knowledge: string[];
  occurrences: number;
  successRate: number | null;
  successfulRuns: number;
  failedRuns: number;
  lastSeen?: string;
}

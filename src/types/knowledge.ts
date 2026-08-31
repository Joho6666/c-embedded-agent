export interface KnowledgeDoc {
  id: string;
  title: string;
  category: "STM32" | "ESP32" | "C Language" | "RTOS";
  source: string;
  version: string;
  updatedAt: string;
  pages?: number;
  format: string;
  docCount: number;
  indexed: boolean;
  subtitle?: string;
}

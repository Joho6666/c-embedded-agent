export type KnowledgeOrigin = "official" | "project" | "user" | "memory" | "skill";

export type KnowledgeSourceType =
  | "datasheet"
  | "reference_manual"
  | "hal"
  | "cmsis"
  | "example"
  | "application_note"
  | "errata"
  | "user_document"
  | "official"
  | "project"
  | "user"
  | "memory"
  | "skill";

export interface KnowledgeDocument {
  id: string;
  title: string;
  subtitle?: string;
  vendor: string;
  platform: string;
  mcuFamilies: string[];
  framework?: string;
  version: string;
  sourceType: KnowledgeSourceType;
  origin?: KnowledgeOrigin;
  category: "STM32" | "ESP32" | "C Language" | "RTOS";
  url?: string;
  localPath?: string;
  pages?: number;
  chunks: number;
  docCount: number;
  format: string;
  indexed: boolean;
  embeddingModel?: string;
  contentHash?: string;
  indexedAt?: string;
  updatedAt: string;
  source: string;
}

export type KnowledgeDoc = KnowledgeDocument;

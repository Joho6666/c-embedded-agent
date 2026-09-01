import type { ProviderTemplate } from "@/types";

export const defaultBaseUrls: Record<ProviderTemplate, string> = {
  openai: "https://api.openai.com/v1",
  anthropic: "https://api.anthropic.com",
  gemini: "https://generativelanguage.googleapis.com/v1beta",
  openrouter: "https://openrouter.ai/api/v1",
  newapi: "https://newapi.example.com/v1",
  oneapi: "https://oneapi.example.com/v1",
  custom: "https://api.example.com/v1",
};

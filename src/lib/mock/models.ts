import type { CapabilityKind, RealModel } from "@/types";

type Cap = CapabilityKind;

const T: Cap[] = ["chat", "tools", "streaming"];
const TV: Cap[] = ["chat", "tools", "vision", "streaming"];
const TR: Cap[] = ["chat", "tools", "reasoning", "streaming"];
const TC: Cap[] = ["chat", "tools", "coding", "streaming"];
const TVC: Cap[] = ["chat", "tools", "vision", "coding", "streaming"];
const TVCR: Cap[] = ["chat", "tools", "vision", "coding", "reasoning", "streaming", "json"];
const EMB: Cap[] = ["embedding"];
const IMG: Cap[] = ["image"];
const AUD: Cap[] = ["audio"];
const RESP: Cap[] = ["chat", "responses", "tools", "vision", "coding", "streaming"];

function m(
  id: string,
  providerId: string,
  name: string,
  modelId: string,
  capabilities: Cap[],
  contextWindow: number,
  inputPrice: number,
  outputPrice: number,
  ttftMs: number,
  tokensPerSec: number,
  successRate: number,
  credentialCount: number,
  tags: string[],
  status: RealModel["status"] = "available",
): RealModel {
  return {
    id,
    providerId,
    name,
    modelId,
    capabilities,
    contextWindow,
    inputPrice,
    outputPrice,
    ttftMs,
    tokensPerSec,
    successRate,
    credentialCount,
    tags,
    status,
  };
}

export const realModels: RealModel[] = [
  m("m_oa_gpt", "openai", "GPT Flagship", "gpt-4.1", TVCR, 1_048_576, 2.0, 8.0, 420, 82, 99.7, 3, ["smart", "coding", "vision", "reasoning"]),
  m("m_oa_mini", "openai", "GPT Mini", "gpt-4.1-mini", TVC, 1_048_576, 0.4, 1.6, 280, 120, 99.8, 3, ["fast", "cheap", "coding"]),
  m("m_oa_nano", "openai", "GPT Nano", "gpt-4.1-nano", T, 1_048_576, 0.1, 0.4, 180, 180, 99.9, 2, ["fast", "cheap"]),
  m("m_oa_codex", "openai", "Codex Compatible", "codex-mini", TC, 192_000, 1.5, 6.0, 510, 70, 99.4, 2, ["coding", "agent"]),
  m("m_oa_o", "openai", "o-series Reasoner", "o4-mini", TR, 200_000, 1.1, 4.4, 890, 48, 99.2, 2, ["reasoning", "coding"]),
  m("m_oa_emb", "openai", "text-embedding-3-large", "text-embedding-3-large", EMB, 8191, 0.13, 0, 90, 400, 99.9, 2, ["cheap"]),
  m("m_oa_img", "openai", "GPT Image", "gpt-image-1", IMG, 0, 0, 0, 1400, 0, 98.8, 1, ["vision"]),
  m("m_oa_tts", "openai", "TTS", "gpt-4o-mini-tts", AUD, 0, 0.6, 0, 320, 0, 99.4, 1, []),
  m("m_gm_pro", "gemini", "Gemini Pro", "gemini-2.5-pro", TVCR, 1_048_576, 1.25, 10, 510, 76, 99.3, 3, ["smart", "reasoning", "long-context", "vision"]),
  m("m_gm_flash", "gemini", "Gemini Flash", "gemini-2.5-flash", TVC, 1_048_576, 0.15, 0.6, 240, 160, 99.6, 3, ["fast", "cheap", "coding", "vision"]),
  m("m_gm_lite", "gemini", "Gemini Flash Lite", "gemini-2.5-flash-lite", T, 1_048_576, 0.075, 0.3, 160, 210, 99.8, 2, ["fast", "cheap"]),
  m("m_gm_img", "gemini", "Imagen", "imagen-3", IMG, 0, 0, 0, 1800, 0, 98.1, 1, ["vision"]),
  m("m_gm_emb", "gemini", "gemini-embedding", "text-embedding-004", EMB, 2048, 0.025, 0, 70, 500, 99.9, 2, ["cheap"]),
  m("m_gm_live", "gemini", "Gemini Live", "gemini-2.5-flash-live", ["chat", "audio", "streaming"], 128_000, 0.3, 1.2, 200, 90, 98.6, 1, ["fast"]),
  m("m_ag_code", "antigravity", "Antigravity Coding", "antigravity-code", RESP, 200_000, 0, 0, 640, 55, 98.9, 1, ["coding", "agent"]),
  m("m_ag_chat", "antigravity", "Antigravity Chat", "antigravity-chat", ["chat", "responses", "streaming"], 128_000, 0, 0, 580, 60, 99.0, 1, ["fast"]),
  m("m_an_opus", "anthropic", "Claude Opus", "claude-opus-4", TVCR, 200_000, 15, 75, 980, 42, 99.1, 1, ["smart", "reasoning", "coding", "vision"]),
  m("m_an_sonnet", "anthropic", "Claude Sonnet", "claude-sonnet-4", TVC, 200_000, 3, 15, 620, 68, 99.4, 2, ["coding", "smart", "vision"]),
  m("m_an_haiku", "anthropic", "Claude Haiku", "claude-haiku-3.5", TV, 200_000, 0.8, 4, 310, 140, 99.6, 1, ["fast", "cheap"]),
  m("m_an_code", "anthropic", "Claude Code", "claude-sonnet-4-coding", TC, 200_000, 3, 15, 700, 60, 97.8, 1, ["coding", "agent"], "degraded"),
  m("m_an_think", "anthropic", "Claude Extended Thinking", "claude-sonnet-4-thinking", TR, 200_000, 3, 15, 1400, 28, 98.9, 1, ["reasoning"]),
  m("m_glm_plus", "glm", "GLM-4 Plus", "glm-4-plus", TVC, 128_000, 0.7, 0.7, 480, 90, 99.5, 2, ["coding", "smart"]),
  m("m_glm_air", "glm", "GLM-4 Air", "glm-4-air", T, 128_000, 0.14, 0.14, 260, 150, 99.7, 2, ["fast", "cheap"]),
  m("m_glm_flash", "glm", "GLM Flash", "glm-4-flash", T, 128_000, 0.01, 0.01, 180, 190, 99.8, 2, ["fast", "cheap"]),
  m("m_glm_code", "glm", "GLM Coding", "glm-4-code", TC, 128_000, 0.35, 1.4, 420, 100, 99.4, 1, ["coding"]),
  m("m_kimi_k", "kimi", "Kimi K2", "kimi-k2", TVC, 256_000, 0.6, 2.5, 540, 80, 99.2, 1, ["long-context", "coding"]),
  m("m_kimi_8k", "kimi", "Moonshot 8k", "moonshot-v1-8k", T, 8_000, 0.12, 0.12, 300, 110, 99.4, 1, ["cheap", "fast"]),
  m("m_kimi_128", "kimi", "Moonshot 128k", "moonshot-v1-128k", T, 128_000, 0.6, 0.6, 520, 70, 99.0, 1, ["long-context"]),
  m("m_ds_chat", "deepseek", "DeepSeek Chat", "deepseek-chat", TC, 64_000, 0.14, 0.28, 310, 130, 99.3, 2, ["cheap", "coding", "fast"]),
  m("m_ds_r1", "deepseek", "DeepSeek Reasoner", "deepseek-reasoner", TR, 64_000, 0.55, 2.19, 920, 45, 99.0, 1, ["reasoning", "coding"]),
  m("m_ds_coder", "deepseek", "DeepSeek Coder", "deepseek-coder", TC, 64_000, 0.14, 0.28, 340, 120, 99.1, 1, ["coding", "cheap"]),
  m("m_or_auto", "openrouter", "OpenRouter Auto", "openrouter/auto", TVC, 200_000, 0, 0, 780, 70, 98.4, 1, ["smart"]),
  m("m_or_llama", "openrouter", "Llama 3.3 70B", "meta-llama/llama-3.3-70b", T, 128_000, 0.12, 0.3, 410, 95, 98.8, 1, ["cheap"]),
  m("m_or_qwen", "openrouter", "Qwen 2.5 72B", "qwen/qwen-2.5-72b", TC, 32_000, 0.12, 0.39, 390, 100, 98.6, 1, ["coding", "cheap"]),
  m("m_or_mix", "openrouter", "Mixtral 8x22B", "mistralai/mixtral-8x22b", T, 65_000, 0.9, 0.9, 520, 80, 98.2, 1, []),
  m("m_or_emb", "openrouter", "OR Embedding", "thenlper/gte-large", EMB, 512, 0.01, 0, 80, 600, 99.5, 1, ["cheap"]),
  m("m_volc_pro", "volcengine", "Doubao Pro", "doubao-pro-32k", T, 32_000, 0.8, 2.0, 560, 85, 99.1, 1, ["smart"]),
  m("m_volc_lite", "volcengine", "Doubao Lite", "doubao-lite-32k", T, 32_000, 0.3, 0.6, 340, 140, 99.4, 1, ["fast", "cheap"]),
  m("m_volc_code", "volcengine", "Doubao Coding", "doubao-1.5-pro", TC, 128_000, 0.8, 2.0, 610, 78, 97.0, 1, ["coding"], "degraded"),
  m("m_bl_max", "bailian", "Qwen Max", "qwen-max", TVC, 32_000, 2.4, 9.6, 640, 70, 99.0, 1, ["smart", "vision"]),
  m("m_bl_plus", "bailian", "Qwen Plus", "qwen-plus", T, 131_072, 0.8, 2.0, 480, 90, 99.2, 1, ["long-context"]),
  m("m_bl_turbo", "bailian", "Qwen Turbo", "qwen-turbo", T, 131_072, 0.3, 0.6, 260, 150, 99.5, 1, ["fast", "cheap"]),
  m("m_hy_pro", "hunyuan", "Hunyuan Pro", "hunyuan-pro", T, 32_000, 4.0, 12, 700, 60, 98.8, 1, ["smart"], "degraded"),
  m("m_hy_lite", "hunyuan", "Hunyuan Lite", "hunyuan-lite", T, 256_000, 0, 0, 420, 100, 99.0, 1, ["cheap", "long-context"]),
  m("m_sf_qwen", "siliconflow", "Qwen2.5-72B", "Qwen/Qwen2.5-72B-Instruct", TC, 32_000, 0.41, 0.41, 300, 140, 99.6, 1, ["cheap", "coding", "fast"]),
  m("m_sf_ds", "siliconflow", "DeepSeek-V3 SF", "deepseek-ai/DeepSeek-V3", TC, 64_000, 0.14, 0.28, 280, 150, 99.5, 1, ["cheap", "coding"]),
  m("m_sf_emb", "siliconflow", "BGE-M3", "BAAI/bge-m3", EMB, 8192, 0.02, 0, 60, 700, 99.8, 1, ["cheap"]),
  m("m_ol_qwen", "ollama", "qwen2.5:32b", "qwen2.5:32b", TC, 32_000, 0, 0, 40, 48, 100, 1, ["coding", "cheap"]),
  m("m_ol_llama", "ollama", "llama3.1:8b", "llama3.1:8b", T, 128_000, 0, 0, 22, 90, 100, 1, ["fast", "cheap"]),
  m("m_ol_ds", "ollama", "deepseek-r1:14b", "deepseek-r1:14b", TR, 64_000, 0, 0, 55, 36, 100, 1, ["reasoning"]),
  m("m_ol_nomic", "ollama", "nomic-embed", "nomic-embed-text", EMB, 8192, 0, 0, 12, 800, 100, 1, ["cheap"]),
  m("m_cu_lab", "custom-openai", "lab-chat", "lab-chat-v1", T, 32_000, 0, 0, 210, 80, 99.9, 1, ["cheap"], "unavailable"),
  m("m_cu_code", "custom-openai", "lab-coder", "lab-coder-v1", TC, 32_000, 0, 0, 240, 70, 99.9, 1, ["coding"], "unavailable"),
];

import type { EmbeddingConfig } from "@/lib/types";

/** Model id from the active embedding provider config. */
export function activeEmbeddingModelId(
  cfg: EmbeddingConfig | undefined,
): string {
  if (!cfg) return "";
  if (cfg.provider === "sentence_transformers") {
    return cfg.sentence_transformers.model;
  }
  if (cfg.provider === "ollama") return cfg.ollama.model;
  if (cfg.provider === "openrouter") return cfg.openrouter.model;
  return cfg.gigachat.model;
}

/** Human-readable provider · model label. */
export function activeEmbeddingLabel(
  cfg: EmbeddingConfig | undefined,
): string {
  if (!cfg) return "—";
  const model = activeEmbeddingModelId(cfg);
  return model ? `${cfg.provider} · ${model}` : cfg.provider;
}

import type { EmbeddingConfig, EmbeddingProviderKind } from "@/lib/types";
import type {
  GigachatDraft,
  OllamaDraft,
  OpenRouterDraft,
} from "@/components/provider-settings-types";
import { defaultGigachatDraft } from "@/components/provider-settings-utils";

export type EmbeddingDraft = {
  provider: EmbeddingProviderKind;
  sentence_transformers: { model: string };
  ollama: OllamaDraft;
  openrouter: OpenRouterDraft;
  gigachat: GigachatDraft;
};

export function embeddingDraftFromConfig(cfg: EmbeddingConfig): EmbeddingDraft {
  return {
    provider: cfg.provider,
    sentence_transformers: { ...cfg.sentence_transformers },
    ollama: { ...cfg.ollama },
    openrouter: {
      base_url: cfg.openrouter.base_url,
      api_key: "",
      model: cfg.openrouter.model,
    },
    gigachat: defaultGigachatDraft({
      scope: cfg.gigachat.scope,
      base_url: cfg.gigachat.base_url,
      auth_url: cfg.gigachat.auth_url,
      model: cfg.gigachat.model,
      verify_ssl: cfg.gigachat.verify_ssl,
    }),
  };
}

export const DEFAULT_EMBEDDING_DRAFT: EmbeddingDraft = {
  provider: "sentence_transformers",
  sentence_transformers: {
    model: "sentence-transformers/all-MiniLM-L6-v2",
  },
  ollama: {
    base_url: "http://host.docker.internal:11435",
    model: "nomic-embed-text",
  },
  openrouter: {
    base_url: "https://openrouter.ai/api/v1",
    api_key: "",
    model: "openai/text-embedding-3-small",
  },
  gigachat: defaultGigachatDraft({ model: "Embeddings" }),
};

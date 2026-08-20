import type { LlmConfig, TextLlmProvider } from "@/lib/types";
import type {
  GigachatDraft,
  OllamaDraft,
  OpenRouterDraft,
} from "@/components/provider-settings-types";
import { defaultGigachatDraft } from "@/components/provider-settings-utils";

export type LlmDraft = {
  provider: TextLlmProvider;
  ollama: OllamaDraft;
  openrouter: OpenRouterDraft;
  gigachat: GigachatDraft;
};

export function llmDraftFromConfig(cfg: LlmConfig): LlmDraft {
  return {
    provider: cfg.provider,
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

export const DEFAULT_LLM_DRAFT: LlmDraft = {
  provider: "ollama",
  ollama: {
    base_url: "http://host.docker.internal:11435",
    model: "llama3.2",
  },
  openrouter: {
    base_url: "https://openrouter.ai/api/v1",
    api_key: "",
    model: "openai/gpt-4o-mini",
  },
  gigachat: defaultGigachatDraft(),
};

import type { TextLlmProvider } from "@/lib/types";
import type {
  GigachatDraft,
  OllamaDraft,
  OpenRouterDraft,
} from "@/components/provider-settings-types";
import { defaultGigachatDraft } from "@/components/provider-settings-utils";

export const RERANK_PROVIDER_KEY = "rageval.rerank.provider";

export type RerankProviderKind = TextLlmProvider | "huggingface";

export type RerankDraft = {
  provider: RerankProviderKind;
  huggingface: { model: string };
  ollama: OllamaDraft;
  openrouter: OpenRouterDraft;
  gigachat: GigachatDraft;
};

export const DEFAULT_HF_RERANK = "cross-encoder/ms-marco-MiniLM-L-6-v2";

export const DEFAULT_RERANK_DRAFT: RerankDraft = {
  provider: "huggingface",
  huggingface: { model: DEFAULT_HF_RERANK },
  ollama: {
    base_url: "http://host.docker.internal:11435",
    model: "",
  },
  openrouter: {
    base_url: "https://openrouter.ai/api/v1",
    api_key: "",
    model: "",
  },
  gigachat: defaultGigachatDraft({ model: "" }),
};

export function readStoredRerankProvider(): RerankProviderKind {
  try {
    const raw = localStorage.getItem(RERANK_PROVIDER_KEY);
    if (
      raw === "ollama" ||
      raw === "openrouter" ||
      raw === "gigachat" ||
      raw === "huggingface"
    ) {
      return raw;
    }
  } catch {
    /* ignore */
  }
  return "huggingface";
}

export function writeStoredRerankProvider(provider: RerankProviderKind) {
  try {
    localStorage.setItem(RERANK_PROVIDER_KEY, provider);
  } catch {
    /* ignore */
  }
}

export function selectedRerankModel(draft: RerankDraft): string {
  if (draft.provider === "huggingface") return draft.huggingface.model;
  if (draft.provider === "ollama") return draft.ollama.model;
  if (draft.provider === "openrouter") return draft.openrouter.model;
  return draft.gigachat.model;
}

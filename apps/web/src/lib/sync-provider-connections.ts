import {
  updateEmbeddingConfig,
  updateLlmConfig,
} from "@/lib/api";
import type { GigachatDraft, OllamaDraft, OpenRouterDraft } from "@/components/provider-settings-types";
import { resolveGigachatCredentials } from "@/components/provider-settings-utils";

/** Connection fields shared across Embedding / Text / Reranker tabs. */
export type SharedProviderConnection = {
  ollama: Pick<OllamaDraft, "base_url">;
  openrouter: {
    base_url: string;
    api_key?: string;
  };
  gigachat: {
    credentials?: string;
    scope: string;
    base_url: string;
    auth_url: string;
    verify_ssl: boolean;
  };
};

export function buildSharedConnection(args: {
  ollama: OllamaDraft;
  openrouter: OpenRouterDraft;
  gigachat: GigachatDraft;
  credentialsConfigured: boolean;
  /** When true, missing GigaChat auth is an error (active gigachat provider). */
  requireGigachatAuth?: boolean;
}): { connection?: SharedProviderConnection; error?: string } {
  const resolved = resolveGigachatCredentials(
    args.gigachat,
    args.credentialsConfigured,
  );
  if (resolved.error === "clientPairIncomplete") {
    return { error: resolved.error };
  }
  if (resolved.error === "credentialsRequired" && args.requireGigachatAuth) {
    return { error: resolved.error };
  }
  return {
    connection: {
      ollama: { base_url: args.ollama.base_url },
      openrouter: {
        base_url: args.openrouter.base_url,
        ...(args.openrouter.api_key.trim()
          ? { api_key: args.openrouter.api_key.trim() }
          : {}),
      },
      gigachat: {
        scope: args.gigachat.scope,
        base_url: args.gigachat.base_url,
        auth_url: args.gigachat.auth_url,
        verify_ssl: args.gigachat.verify_ssl,
        ...(resolved.credentials
          ? { credentials: resolved.credentials }
          : {}),
      },
    },
  };
}

/** Keep Ollama / OpenRouter / GigaChat connection settings identical across tabs. */
export async function syncSharedProviderConnections(
  connection: SharedProviderConnection,
  opts?: { skip?: "llm" | "embedding" },
): Promise<void> {
  const tasks: Promise<unknown>[] = [];
  if (opts?.skip !== "llm") {
    tasks.push(
      updateLlmConfig({
        ollama: connection.ollama,
        openrouter: connection.openrouter,
        gigachat: connection.gigachat,
      }),
    );
  }
  if (opts?.skip !== "embedding") {
    tasks.push(
      updateEmbeddingConfig({
        ollama: connection.ollama,
        openrouter: connection.openrouter,
        gigachat: connection.gigachat,
      }),
    );
  }
  await Promise.all(tasks);
}

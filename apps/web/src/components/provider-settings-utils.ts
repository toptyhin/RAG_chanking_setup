import type { RemoteModelInfo } from "@/lib/types";
import type { GigachatDraft, ModelsQueryState } from "@/components/provider-settings-types";

/** GigaChat Basic auth key = Base64(client_id:client_secret). */
export function encodeGigachatCredentials(
  clientId: string,
  clientSecret: string,
): string {
  return btoa(`${clientId}:${clientSecret}`);
}

export function resolveGigachatCredentials(
  draft: GigachatDraft,
  credentialsConfigured: boolean,
): { credentials?: string; error?: "credentialsRequired" | "clientPairIncomplete" } {
  if (draft.authMode === "client") {
    const clientId = draft.clientId.trim();
    const clientSecret = draft.clientSecret.trim();
    if (!clientId && !clientSecret) {
      if (credentialsConfigured) return {};
      return { error: "credentialsRequired" };
    }
    if (!clientId || !clientSecret) {
      return { error: "clientPairIncomplete" };
    }
    return { credentials: encodeGigachatCredentials(clientId, clientSecret) };
  }

  const credentials = draft.credentials.trim();
  if (!credentials) {
    if (credentialsConfigured) return {};
    return { error: "credentialsRequired" };
  }
  return { credentials };
}

export function defaultGigachatDraft(
  overrides?: Partial<GigachatDraft>,
): GigachatDraft {
  return {
    authMode: "client",
    clientId: "",
    clientSecret: "",
    credentials: "",
    scope: "GIGACHAT_API_PERS",
    base_url: "https://gigachat.devices.sberbank.ru/api/v1",
    auth_url: "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
    model: "GigaChat",
    verify_ssl: true,
    ...overrides,
  };
}

/** Normalize react-query model-list results for RemoteModelPicker. */
export function toModelsQueryState(
  query: {
    data?: {
      ok: boolean;
      items?: RemoteModelInfo[];
      message?: string | null;
    };
    isFetching: boolean;
    isError: boolean;
    error: unknown;
    refetch: () => unknown;
  },
  emptyHint: string,
  failedFallback: string,
): ModelsQueryState {
  return {
    items: query.data?.ok ? (query.data.items ?? []) : [],
    loading: query.isFetching,
    error:
      query.data && !query.data.ok
        ? (query.data.message ?? failedFallback)
        : query.isError
          ? (query.error as Error).message
          : null,
    emptyHint,
    onRefresh: () => void query.refetch(),
  };
}

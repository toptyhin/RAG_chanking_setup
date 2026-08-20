import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  getLlmConfig,
  listLlmModels,
  testLlmConnection,
  updateLlmConfig,
} from "@/lib/api";
import { useI18n } from "@/lib/locale";
import type { LlmConfig } from "@/lib/types";
import {
  defaultGigachatDraft,
  resolveGigachatCredentials,
} from "@/components/provider-settings-utils";
import {
  buildSharedConnection,
  syncSharedProviderConnections,
} from "@/lib/sync-provider-connections";
import {
  DEFAULT_LLM_DRAFT,
  llmDraftFromConfig,
  type LlmDraft,
} from "@/components/llm-provider-form-types";

export function useLlmProviderForm() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [draft, setDraft] = useState<LlmDraft>(DEFAULT_LLM_DRAFT);
  const [formError, setFormError] = useState<string | null>(null);
  const [testMessage, setTestMessage] = useState<string | null>(null);
  const [testOk, setTestOk] = useState<boolean | null>(null);
  const [debouncedOllamaUrl, setDebouncedOllamaUrl] = useState(
    DEFAULT_LLM_DRAFT.ollama.base_url,
  );

  const config = useQuery({
    queryKey: ["llm", "config"],
    queryFn: getLlmConfig,
  });

  useEffect(() => {
    if (config.data) {
      setDraft(llmDraftFromConfig(config.data));
      setDebouncedOllamaUrl(config.data.ollama.base_url);
      setFormError(null);
    }
  }, [config.data]);

  useEffect(() => {
    const id = window.setTimeout(() => {
      setDebouncedOllamaUrl(draft.ollama.base_url.trim());
    }, 400);
    return () => window.clearTimeout(id);
  }, [draft.ollama.base_url]);

  const credentialsConfigured = Boolean(
    config.data?.gigachat.credentials_configured,
  );

  const ollamaModels = useQuery({
    queryKey: ["llm", "models", "ollama", debouncedOllamaUrl],
    queryFn: () =>
      listLlmModels({
        provider: "ollama",
        ollama: { base_url: debouncedOllamaUrl },
        purpose: "text",
      }),
    enabled:
      draft.provider === "ollama" &&
      debouncedOllamaUrl.startsWith("http") &&
      debouncedOllamaUrl.length > 10,
    staleTime: 30_000,
    retry: false,
  });

  useEffect(() => {
    if (draft.provider !== "ollama") return;
    const models = ollamaModels.data?.ok ? ollamaModels.data.models : [];
    if (models.length === 0) return;
    setDraft((prev) => {
      if (models.includes(prev.ollama.model)) return prev;
      return {
        ...prev,
        ollama: { ...prev.ollama, model: models[0] },
      };
    });
  }, [draft.provider, ollamaModels.data]);

  const openrouterModels = useQuery({
    queryKey: [
      "llm",
      "models",
      "openrouter",
      draft.openrouter.base_url,
      draft.openrouter.api_key ? "draft-key" : "saved-key",
      config.data?.openrouter.api_key_configured ?? false,
    ],
    queryFn: () =>
      listLlmModels({
        provider: "openrouter",
        purpose: "text",
        openrouter: {
          base_url: draft.openrouter.base_url,
          model: draft.openrouter.model,
          ...(draft.openrouter.api_key.trim()
            ? { api_key: draft.openrouter.api_key.trim() }
            : {}),
        },
      }),
    enabled:
      draft.provider === "openrouter" &&
      (Boolean(draft.openrouter.api_key.trim()) ||
        Boolean(config.data?.openrouter.api_key_configured)),
    staleTime: 60_000,
    retry: false,
  });

  const gigachatModels = useQuery({
    queryKey: [
      "llm",
      "models",
      "gigachat",
      draft.gigachat.base_url,
      draft.gigachat.scope,
      draft.gigachat.authMode,
      draft.gigachat.clientId,
      draft.gigachat.clientSecret ? "draft-secret" : "",
      draft.gigachat.credentials ? "draft-creds" : "",
      credentialsConfigured,
    ],
    queryFn: () => {
      const resolved = resolveGigachatCredentials(
        draft.gigachat,
        credentialsConfigured,
      );
      if (resolved.error) {
        return Promise.resolve({
          ok: false as const,
          provider: "gigachat" as const,
          models: [],
          items: [],
          message:
            resolved.error === "clientPairIncomplete"
              ? t("providerForm.clientPairIncomplete")
              : t("providerForm.credentialsRequired"),
        });
      }
      return listLlmModels({
        provider: "gigachat",
        purpose: "text",
        gigachat: {
          scope: draft.gigachat.scope,
          base_url: draft.gigachat.base_url,
          auth_url: draft.gigachat.auth_url,
          model: draft.gigachat.model,
          verify_ssl: draft.gigachat.verify_ssl,
          ...(resolved.credentials
            ? { credentials: resolved.credentials }
            : {}),
        },
      });
    },
    enabled:
      draft.provider === "gigachat" &&
      (credentialsConfigured ||
        (draft.gigachat.authMode === "api_key" &&
          Boolean(draft.gigachat.credentials.trim())) ||
        (draft.gigachat.authMode === "client" &&
          Boolean(draft.gigachat.clientId.trim()) &&
          Boolean(draft.gigachat.clientSecret.trim()))),
    staleTime: 60_000,
    retry: false,
  });

  const buildGigachatPayload = () => {
    const resolved = resolveGigachatCredentials(
      draft.gigachat,
      credentialsConfigured,
    );
    if (resolved.error) {
      const message =
        resolved.error === "clientPairIncomplete"
          ? t("providerForm.clientPairIncomplete")
          : t("providerForm.credentialsRequired");
      return { error: message };
    }
    return {
      payload: {
        scope: draft.gigachat.scope,
        base_url: draft.gigachat.base_url,
        auth_url: draft.gigachat.auth_url,
        model: draft.gigachat.model,
        verify_ssl: draft.gigachat.verify_ssl,
        ...(resolved.credentials
          ? { credentials: resolved.credentials }
          : {}),
      },
    };
  };

  const save = useMutation({
    mutationFn: async () => {
      const gigachat =
        draft.provider === "gigachat" ? buildGigachatPayload() : null;
      if (gigachat?.error) {
        throw new Error(gigachat.error);
      }
      const shared = buildSharedConnection({
        ollama: draft.ollama,
        openrouter: draft.openrouter,
        gigachat: draft.gigachat,
        credentialsConfigured,
        requireGigachatAuth: draft.provider === "gigachat",
      });
      if (shared.error) {
        throw new Error(
          shared.error === "clientPairIncomplete"
            ? t("providerForm.clientPairIncomplete")
            : t("providerForm.credentialsRequired"),
        );
      }
      const data = await updateLlmConfig({
        provider: draft.provider,
        ollama: draft.ollama,
        openrouter: {
          base_url: draft.openrouter.base_url,
          model: draft.openrouter.model,
          ...(draft.openrouter.api_key.trim()
            ? { api_key: draft.openrouter.api_key.trim() }
            : {}),
        },
        gigachat:
          gigachat?.payload ?? {
            scope: draft.gigachat.scope,
            base_url: draft.gigachat.base_url,
            auth_url: draft.gigachat.auth_url,
            model: draft.gigachat.model,
            verify_ssl: draft.gigachat.verify_ssl,
          },
      });
      if (shared.connection) {
        await syncSharedProviderConnections(shared.connection, {
          skip: "llm",
        });
      }
      return data;
    },
    onSuccess: async (data) => {
      setFormError(null);
      setTestMessage(null);
      setTestOk(null);
      setDraft(llmDraftFromConfig(data));
      await qc.invalidateQueries({ queryKey: ["llm"] });
      await qc.invalidateQueries({ queryKey: ["embedding", "config"] });
    },
    onError: (err) => {
      setFormError(err instanceof Error ? err.message : String(err));
    },
  });

  const test = useMutation({
    mutationFn: () => {
      const gigachat =
        draft.provider === "gigachat" ? buildGigachatPayload() : null;
      if (gigachat?.error) {
        throw new Error(gigachat.error);
      }
      return testLlmConnection({
        provider: draft.provider,
        ollama: draft.ollama,
        openrouter: {
          base_url: draft.openrouter.base_url,
          model: draft.openrouter.model,
          ...(draft.openrouter.api_key.trim()
            ? { api_key: draft.openrouter.api_key.trim() }
            : {}),
        },
        gigachat:
          gigachat?.payload ?? {
            scope: draft.gigachat.scope,
            base_url: draft.gigachat.base_url,
            auth_url: draft.gigachat.auth_url,
            model: draft.gigachat.model,
            verify_ssl: draft.gigachat.verify_ssl,
          },
      });
    },
    onSuccess: (data) => {
      setFormError(null);
      setTestOk(data.ok);
      const modelsHint =
        data.models.length > 0
          ? ` · ${data.models.slice(0, 5).join(", ")}${data.models.length > 5 ? "…" : ""}`
          : "";
      setTestMessage(
        `${data.message} (${Math.round(data.latency_ms)} ms)${modelsHint}`,
      );
      if (data.ok && data.provider === "ollama") {
        void qc.invalidateQueries({ queryKey: ["llm", "models", "ollama"] });
      }
    },
    onError: (err) => {
      setTestOk(false);
      setTestMessage(err instanceof Error ? err.message : String(err));
    },
  });

  return {
    t,
    config,
    cfg: config.data as LlmConfig | undefined,
    draft,
    setDraft,
    formError,
    setFormError,
    testMessage,
    testOk,
    credentialsConfigured,
    ollamaModels,
    openrouterModels,
    gigachatModels,
    save,
    test,
  };
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  getCurrentRerank,
  getLlmConfig,
  listLlmModels,
  setCurrentRerank,
  testLlmConnection,
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
  DEFAULT_HF_RERANK,
  DEFAULT_RERANK_DRAFT,
  readStoredRerankProvider,
  selectedRerankModel,
  writeStoredRerankProvider,
  type RerankDraft,
  type RerankProviderKind,
} from "@/components/rerank-model-form-types";

export function useRerankModelForm() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [draft, setDraft] = useState<RerankDraft>(DEFAULT_RERANK_DRAFT);
  const [formError, setFormError] = useState<string | null>(null);
  const [testMessage, setTestMessage] = useState<string | null>(null);
  const [testOk, setTestOk] = useState<boolean | null>(null);
  const [debouncedOllamaUrl, setDebouncedOllamaUrl] = useState(
    DEFAULT_RERANK_DRAFT.ollama.base_url,
  );

  const current = useQuery({
    queryKey: ["models", "rerank", "current"],
    queryFn: getCurrentRerank,
  });

  const config = useQuery({
    queryKey: ["llm", "config"],
    queryFn: getLlmConfig,
  });

  useEffect(() => {
    const localProvider = readStoredRerankProvider();
    const serverProvider = current.data?.provider;
    const provider: RerankProviderKind =
      serverProvider === "ollama" ||
      serverProvider === "huggingface" ||
      serverProvider === "openrouter" ||
      serverProvider === "gigachat"
        ? serverProvider
        : localProvider;
    writeStoredRerankProvider(provider);
    const modelId = current.data?.model_id ?? DEFAULT_HF_RERANK;
    if (!config.data) {
      setDraft((prev) => ({
        ...prev,
        provider,
        huggingface: { model: modelId },
      }));
      return;
    }
    const cfg = config.data;
    setDraft({
      provider,
      huggingface: { model: provider === "huggingface" ? modelId : DEFAULT_HF_RERANK },
      ollama: {
        base_url: cfg.ollama.base_url,
        model: provider === "ollama" ? modelId : "",
      },
      openrouter: {
        base_url: cfg.openrouter.base_url,
        api_key: "",
        model: provider === "openrouter" ? modelId : "",
      },
      gigachat: defaultGigachatDraft({
        scope: cfg.gigachat.scope,
        base_url: cfg.gigachat.base_url,
        auth_url: cfg.gigachat.auth_url,
        model: provider === "gigachat" ? modelId : "",
        verify_ssl: cfg.gigachat.verify_ssl,
      }),
    });
    setDebouncedOllamaUrl(cfg.ollama.base_url);
  }, [config.data, current.data?.model_id]);

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
    queryKey: ["rerank", "models", "ollama", debouncedOllamaUrl],
    queryFn: () =>
      listLlmModels({
        provider: "ollama",
        purpose: "rerank",
        ollama: { base_url: debouncedOllamaUrl },
      }),
    enabled:
      draft.provider === "ollama" &&
      debouncedOllamaUrl.startsWith("http") &&
      debouncedOllamaUrl.length > 10,
    staleTime: 30_000,
    retry: false,
  });

  const openrouterModels = useQuery({
    queryKey: [
      "rerank",
      "models",
      "openrouter",
      draft.openrouter.base_url,
      draft.openrouter.api_key ? "draft-key" : "saved-key",
      config.data?.openrouter.api_key_configured ?? false,
    ],
    queryFn: () =>
      listLlmModels({
        provider: "openrouter",
        purpose: "rerank",
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
      "rerank",
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
        purpose: "rerank",
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
      const model = selectedRerankModel(draft).trim();
      if (!model) {
        throw new Error(t("remoteModelPicker.manualPlaceholder"));
      }

      if (draft.provider !== "huggingface") {
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
        if (shared.connection) {
          await syncSharedProviderConnections(shared.connection);
        }
      }

      writeStoredRerankProvider(draft.provider);
      return setCurrentRerank(model, draft.provider);
    },
    onSuccess: async (data) => {
      setFormError(null);
      setTestMessage(null);
      setTestOk(null);
      setDraft((prev) => {
        if (prev.provider === "huggingface") {
          return { ...prev, huggingface: { model: data.model_id } };
        }
        if (prev.provider === "ollama") {
          return { ...prev, ollama: { ...prev.ollama, model: data.model_id } };
        }
        if (prev.provider === "openrouter") {
          return {
            ...prev,
            openrouter: { ...prev.openrouter, model: data.model_id },
          };
        }
        return {
          ...prev,
          gigachat: { ...prev.gigachat, model: data.model_id },
        };
      });
      await qc.invalidateQueries({ queryKey: ["models", "rerank"] });
      await qc.invalidateQueries({ queryKey: ["llm", "config"] });
      await qc.invalidateQueries({ queryKey: ["embedding", "config"] });
    },
    onError: (err) => {
      setFormError(err instanceof Error ? err.message : String(err));
    },
  });

  const test = useMutation({
    mutationFn: () => {
      if (draft.provider === "huggingface") {
        return Promise.resolve({
          ok: true,
          latency_ms: 0,
          message: draft.huggingface.model,
          provider: "ollama" as const,
          model: draft.huggingface.model,
          models: [] as string[],
        });
      }
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
        draft.provider === "huggingface"
          ? data.message
          : `${data.message} (${Math.round(data.latency_ms)} ms)${modelsHint}`,
      );
    },
    onError: (err) => {
      setTestOk(false);
      setTestMessage(err instanceof Error ? err.message : String(err));
    },
  });

  return {
    t,
    current,
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

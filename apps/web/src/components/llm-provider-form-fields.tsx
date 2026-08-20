"use client";

import type { TextLlmProvider } from "@/lib/types";
import {
  GigachatProviderFields,
  OllamaProviderFields,
  OpenRouterProviderFields,
  ProviderFormActions,
  ProviderSelect,
  ProviderTestResult,
} from "@/components/provider-settings";
import { toModelsQueryState } from "@/components/provider-settings-utils";
import { ErrorBox } from "@/components/ui";
import type { useLlmProviderForm } from "@/components/use-llm-provider-form";

type FormState = ReturnType<typeof useLlmProviderForm>;

type Props = Pick<
  FormState,
  | "t"
  | "cfg"
  | "draft"
  | "setDraft"
  | "formError"
  | "setFormError"
  | "testMessage"
  | "testOk"
  | "credentialsConfigured"
  | "ollamaModels"
  | "openrouterModels"
  | "gigachatModels"
  | "save"
  | "test"
>;

export function LlmProviderFormFields({
  t,
  cfg,
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
}: Props) {
  const failed = t("remoteModelPicker.failed");

  return (
    <div className="grid gap-4">
      <ProviderSelect
        value={draft.provider}
        onChange={(value) =>
          setDraft((prev) => ({
            ...prev,
            provider: value as TextLlmProvider,
          }))
        }
        options={[
          { value: "ollama", label: t("providerForm.providerOllama") },
          {
            value: "openrouter",
            label: t("providerForm.providerOpenrouter"),
          },
          { value: "gigachat", label: t("providerForm.providerGigachat") },
        ]}
        hint={t("llmForm.providerHint")}
        extraHint={t("providerForm.connectionShared")}
      />

      {draft.provider === "ollama" ? (
        <OllamaProviderFields
          value={draft.ollama}
          onChange={(ollama) => setDraft((prev) => ({ ...prev, ollama }))}
          dockerHint={t("providerForm.ollamaDockerHint")}
          models={toModelsQueryState(
            ollamaModels,
            t("providerForm.modelsEmpty"),
            failed,
          )}
        />
      ) : null}

      {draft.provider === "openrouter" ? (
        <OpenRouterProviderFields
          value={draft.openrouter}
          onChange={(openrouter) =>
            setDraft((prev) => ({ ...prev, openrouter }))
          }
          secrets={{
            apiKeyConfigured: cfg?.openrouter.api_key_configured,
            apiKeyMasked: cfg?.openrouter.api_key_masked,
          }}
          models={toModelsQueryState(
            openrouterModels,
            cfg?.openrouter.api_key_configured || draft.openrouter.api_key.trim()
              ? t("remoteModelPicker.empty")
              : t("providerForm.apiKeyHint"),
            failed,
          )}
        />
      ) : null}

      {draft.provider === "gigachat" ? (
        <GigachatProviderFields
          value={draft.gigachat}
          onChange={(gigachat) => setDraft((prev) => ({ ...prev, gigachat }))}
          secrets={{
            credentialsConfigured,
            credentialsMasked: cfg?.gigachat.credentials_masked,
          }}
          models={toModelsQueryState(
            gigachatModels,
            credentialsConfigured ||
              draft.gigachat.credentials.trim() ||
              (draft.gigachat.clientId.trim() &&
                draft.gigachat.clientSecret.trim())
              ? t("remoteModelPicker.empty")
              : t("providerForm.credentialsRequired"),
            failed,
          )}
        />
      ) : null}

      <ProviderFormActions
        savePending={save.isPending}
        testPending={test.isPending}
        onSave={() => {
          setFormError(null);
          save.mutate();
        }}
        onTest={() => {
          setFormError(null);
          test.mutate();
        }}
      />

      {formError ? <ErrorBox message={formError} /> : null}
      {save.isError && !formError ? (
        <ErrorBox message={(save.error as Error).message} />
      ) : null}
      {save.isSuccess && !formError ? (
        <p className="text-sm text-[var(--muted)]">{t("providerForm.saved")}</p>
      ) : null}
      <ProviderTestResult message={testMessage} ok={testOk} />
    </div>
  );
}

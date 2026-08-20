"use client";

import { useI18n } from "@/lib/locale";
import { RemoteModelPicker } from "@/components/remote-model-picker";
import type {
  GigachatAuthMode,
  GigachatDraft,
  ModelsQueryState,
  OllamaDraft,
  OpenRouterDraft,
  SecretHints,
} from "@/components/provider-settings-types";
import { Button, Input, Label, Select } from "@/components/ui";

type ProviderSelectProps = {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  hint?: string;
  extraHint?: string;
};

export function ProviderSelect({
  value,
  onChange,
  options,
  hint,
  extraHint,
}: ProviderSelectProps) {
  const { t } = useI18n();
  return (
    <div>
      <Label>{t("providerForm.provider")}</Label>
      <Select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </Select>
      {hint ? (
        <p className="mt-1 text-xs text-[var(--muted)]">{hint}</p>
      ) : null}
      {extraHint ? (
        <p className="mt-2 text-xs text-[var(--muted)]">{extraHint}</p>
      ) : null}
    </div>
  );
}

type OllamaFieldsProps = {
  value: OllamaDraft;
  onChange: (next: OllamaDraft) => void;
  models: ModelsQueryState;
  dockerHint?: string;
};

/** OpenRouter-style layout: Base URL → model picker. */
export function OllamaProviderFields({
  value,
  onChange,
  models,
  dockerHint,
}: OllamaFieldsProps) {
  const { t } = useI18n();
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="sm:col-span-2">
        <Label>{t("providerForm.baseUrl")}</Label>
        <Input
          value={value.base_url}
          onChange={(e) => onChange({ ...value, base_url: e.target.value })}
        />
        {dockerHint ? (
          <p className="mt-1 text-xs text-[var(--muted)]">{dockerHint}</p>
        ) : null}
      </div>
      <div className="sm:col-span-2">
        <RemoteModelPicker
          value={value.model}
          onChange={(model) => onChange({ ...value, model })}
          items={models.items}
          loading={models.loading}
          error={models.error}
          onRefresh={models.onRefresh}
          emptyHint={models.emptyHint}
        />
      </div>
    </div>
  );
}

type OpenRouterFieldsProps = {
  value: OpenRouterDraft;
  onChange: (next: OpenRouterDraft) => void;
  secrets?: SecretHints;
  models: ModelsQueryState;
};

/** Canonical provider settings template (text / OpenRouter). */
export function OpenRouterProviderFields({
  value,
  onChange,
  secrets,
  models,
}: OpenRouterFieldsProps) {
  const { t } = useI18n();
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="sm:col-span-2">
        <Label>{t("providerForm.baseUrl")}</Label>
        <Input
          value={value.base_url}
          onChange={(e) => onChange({ ...value, base_url: e.target.value })}
        />
      </div>
      <div className="sm:col-span-2">
        <Label>{t("providerForm.apiKey")}</Label>
        <Input
          type="password"
          autoComplete="off"
          placeholder={
            secrets?.apiKeyConfigured
              ? (secrets.apiKeyMasked ?? t("providerForm.secretConfigured"))
              : t("providerForm.apiKeyPlaceholder")
          }
          value={value.api_key}
          onChange={(e) => onChange({ ...value, api_key: e.target.value })}
        />
        <p className="mt-1 text-xs text-[var(--muted)]">
          {secrets?.apiKeyConfigured
            ? t("providerForm.secretLeaveBlank")
            : t("providerForm.apiKeyHint")}
        </p>
      </div>
      <div className="sm:col-span-2">
        <RemoteModelPicker
          value={value.model}
          onChange={(model) => onChange({ ...value, model })}
          items={models.items}
          loading={models.loading}
          error={models.error}
          onRefresh={models.onRefresh}
          emptyHint={models.emptyHint}
        />
      </div>
    </div>
  );
}

type GigachatFieldsProps = {
  value: GigachatDraft;
  onChange: (next: GigachatDraft) => void;
  secrets?: SecretHints;
  models: ModelsQueryState;
};

/** Same OpenRouter-style stack: connection → model → advanced URLs. */
export function GigachatProviderFields({
  value,
  onChange,
  secrets,
  models,
}: GigachatFieldsProps) {
  const { t } = useI18n();
  const credentialsConfigured = Boolean(secrets?.credentialsConfigured);

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="sm:col-span-2">
        <Label>{t("providerForm.baseUrl")}</Label>
        <Input
          value={value.base_url}
          onChange={(e) => onChange({ ...value, base_url: e.target.value })}
        />
      </div>

      <div className="sm:col-span-2">
        <Label>{t("providerForm.authMode")}</Label>
        <Select
          value={value.authMode}
          onChange={(e) =>
            onChange({
              ...value,
              authMode: e.target.value as GigachatAuthMode,
            })
          }
        >
          <option value="client">{t("providerForm.authModeClient")}</option>
          <option value="api_key">{t("providerForm.authModeApiKey")}</option>
        </Select>
        <p className="mt-1 text-xs text-[var(--muted)]">
          {t("providerForm.authModeHint")}
        </p>
      </div>

      {value.authMode === "client" ? (
        <>
          <div className="sm:col-span-2">
            <Label>{t("providerForm.clientId")}</Label>
            <Input
              autoComplete="off"
              placeholder={
                credentialsConfigured
                  ? t("providerForm.secretConfigured")
                  : t("providerForm.clientIdPlaceholder")
              }
              value={value.clientId}
              onChange={(e) =>
                onChange({ ...value, clientId: e.target.value })
              }
            />
          </div>
          <div className="sm:col-span-2">
            <Label>{t("providerForm.clientSecret")}</Label>
            <Input
              type="password"
              autoComplete="off"
              placeholder={
                credentialsConfigured
                  ? t("providerForm.secretConfigured")
                  : t("providerForm.clientSecretPlaceholder")
              }
              value={value.clientSecret}
              onChange={(e) =>
                onChange({ ...value, clientSecret: e.target.value })
              }
            />
            <p className="mt-1 text-xs text-[var(--muted)]">
              {credentialsConfigured
                ? t("providerForm.secretLeaveBlank")
                : t("providerForm.clientPairHint")}
            </p>
          </div>
        </>
      ) : (
        <div className="sm:col-span-2">
          <Label>{t("providerForm.credentials")}</Label>
          <Input
            type="password"
            autoComplete="off"
            placeholder={
              credentialsConfigured
                ? (secrets?.credentialsMasked ??
                  t("providerForm.secretConfigured"))
                : t("providerForm.credentialsPlaceholder")
            }
            value={value.credentials}
            onChange={(e) =>
              onChange({ ...value, credentials: e.target.value })
            }
          />
          <p className="mt-1 text-xs text-[var(--muted)]">
            {credentialsConfigured
              ? t("providerForm.secretLeaveBlank")
              : t("providerForm.credentialsHint")}
          </p>
        </div>
      )}

      <div className="sm:col-span-2">
        <Label>{t("providerForm.scope")}</Label>
        <Select
          value={value.scope}
          onChange={(e) => onChange({ ...value, scope: e.target.value })}
        >
          <option value="GIGACHAT_API_PERS">GIGACHAT_API_PERS</option>
          <option value="GIGACHAT_API_B2B">GIGACHAT_API_B2B</option>
          <option value="GIGACHAT_API_CORP">GIGACHAT_API_CORP</option>
        </Select>
      </div>

      <div className="sm:col-span-2">
        <RemoteModelPicker
          value={value.model}
          onChange={(model) => onChange({ ...value, model })}
          items={models.items}
          loading={models.loading}
          error={models.error}
          onRefresh={models.onRefresh}
          emptyHint={models.emptyHint}
        />
      </div>

      <div className="sm:col-span-2">
        <Label>{t("providerForm.authUrl")}</Label>
        <Input
          value={value.auth_url}
          onChange={(e) => onChange({ ...value, auth_url: e.target.value })}
        />
      </div>

      <label className="flex items-center gap-2 text-sm sm:col-span-2">
        <input
          type="checkbox"
          checked={value.verify_ssl}
          onChange={(e) =>
            onChange({ ...value, verify_ssl: e.target.checked })
          }
        />
        {t("providerForm.verifySsl")}
      </label>
    </div>
  );
}

type ProviderFormActionsProps = {
  savePending?: boolean;
  testPending?: boolean;
  onSave: () => void;
  onTest: () => void;
};

export function ProviderFormActions({
  savePending,
  testPending,
  onSave,
  onTest,
}: ProviderFormActionsProps) {
  const { t } = useI18n();
  return (
    <div className="flex flex-wrap gap-2">
      <Button type="button" disabled={savePending} onClick={onSave}>
        {savePending ? t("providerForm.saving") : t("providerForm.save")}
      </Button>
      <Button
        type="button"
        className="bg-transparent text-[var(--fg)] ring-1 ring-[var(--border)]"
        disabled={testPending}
        onClick={onTest}
      >
        {testPending ? t("providerForm.testing") : t("providerForm.test")}
      </Button>
    </div>
  );
}

type TestResultProps = {
  message: string | null;
  ok: boolean | null;
};

export function ProviderTestResult({ message, ok }: TestResultProps) {
  const { t } = useI18n();
  if (!message) return null;
  return (
    <p
      className={`rounded-md border px-3 py-2 text-sm ${
        ok
          ? "border-[var(--border)] bg-[var(--bg)]/60 text-[var(--fg)]"
          : "border-[var(--danger-border)] bg-[var(--danger-bg)] text-[var(--danger)]"
      }`}
    >
      {ok ? t("providerForm.testOk") : t("providerForm.testFail")}: {message}
    </p>
  );
}

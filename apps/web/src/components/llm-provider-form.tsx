"use client";

import { LlmProviderFormFields } from "@/components/llm-provider-form-fields";
import { useLlmProviderForm } from "@/components/use-llm-provider-form";
import { ErrorBox } from "@/components/ui";

export function LlmProviderForm() {
  const form = useLlmProviderForm();
  const { t, config } = form;

  if (config.isLoading) {
    return <p className="text-sm text-[var(--muted)]">{t("common.loading")}</p>;
  }
  if (config.isError) {
    return <ErrorBox message={(config.error as Error).message} />;
  }

  return <LlmProviderFormFields {...form} />;
}

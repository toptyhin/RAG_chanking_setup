"use client";

import { EmbeddingProviderFormFields } from "@/components/embedding-provider-form-fields";
import { useEmbeddingProviderForm } from "@/components/use-embedding-provider-form";
import { ErrorBox } from "@/components/ui";

export function EmbeddingProviderForm() {
  const form = useEmbeddingProviderForm();
  const { t, config } = form;

  if (config.isLoading) {
    return <p className="text-sm text-[var(--muted)]">{t("common.loading")}</p>;
  }
  if (config.isError) {
    return <ErrorBox message={(config.error as Error).message} />;
  }

  return <EmbeddingProviderFormFields {...form} />;
}

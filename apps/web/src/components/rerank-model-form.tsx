"use client";

import { RerankModelFormFields } from "@/components/rerank-model-form-fields";
import { useRerankModelForm } from "@/components/use-rerank-model-form";
import { ErrorBox } from "@/components/ui";

export function RerankModelForm() {
  const form = useRerankModelForm();
  const { t, current, config } = form;

  if (current.isLoading || config.isLoading) {
    return <p className="text-sm text-[var(--muted)]">{t("common.loading")}</p>;
  }
  if (current.isError) {
    return <ErrorBox message={(current.error as Error).message} />;
  }
  if (config.isError) {
    return <ErrorBox message={(config.error as Error).message} />;
  }

  return <RerankModelFormFields {...form} />;
}

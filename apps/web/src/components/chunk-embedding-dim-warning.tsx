"use client";

import { Callout } from "@/components/ui";
import { isEmbeddingDimBelowChunkSize } from "@/lib/chunk-embedding-fit";
import { useI18n } from "@/lib/locale";

export function ChunkEmbeddingDimWarning({
  embeddingDimension,
  chunkSize,
  className = "",
}: {
  embeddingDimension: number | null | undefined;
  chunkSize: number | null | undefined;
  className?: string;
}) {
  const { t } = useI18n();
  if (!isEmbeddingDimBelowChunkSize(embeddingDimension, chunkSize)) {
    return null;
  }

  return (
    <Callout tone="warning" className={className}>
      <strong>{t("chunkEmbeddingFit.warningTitle")}</strong>{" "}
      {t("chunkEmbeddingFit.warningBody", {
        dimension: embeddingDimension ?? 0,
        chunkSize: chunkSize ?? 0,
      })}
    </Callout>
  );
}

import type { TranslationKey } from "@/i18n";

type T = (key: TranslationKey, vars?: Record<string, string | number>) => string;

export function configLabel(config: Record<string, unknown>, t: T): string {
  return Object.entries(config)
    .map(([key, value]) => {
      const labels: Record<string, string> = {
        "embedding.model": t("runPage.configEmbedding"),
        "retrieval.mode": t("runPage.configSearchMode"),
        "retrieval.top_k": t("runPage.configTopK"),
        quantization: t("runPage.configQuantization"),
        "rerank.enabled": t("runPage.configRerank"),
        "prep.pipeline": t("runPage.configPrepPipeline"),
        "chunk.size": t("runPage.configChunkSize"),
        "chunk.overlap": t("runPage.configChunkOverlap"),
      };
      const display =
        typeof value === "boolean"
          ? t(value ? "runPage.on" : "runPage.off")
          : String(value);
      return `${labels[key] ?? key}: ${display}`;
    })
    .join(" · ");
}

export function statusLabel(status: string, t: T): string {
  const labels: Record<
    string,
    | "runPage.statusPending"
    | "runPage.statusRunning"
    | "runPage.statusCompleted"
    | "runPage.statusFailed"
  > = {
    pending: "runPage.statusPending",
    running: "runPage.statusRunning",
    completed: "runPage.statusCompleted",
    failed: "runPage.statusFailed",
  };
  return labels[status] ? t(labels[status]) : t("runPage.statusUnknown");
}

export function modeLabel(mode: string, t: T): string {
  if (mode === "prep") return t("runPage.modePrep");
  if (mode === "chunk") return t("runPage.modeChunk");
  return t("runPage.modeRetrieval");
}

export function scopeLabel(mode: string, t: T): string {
  if (mode === "prep") return t("runPage.scopePrep");
  if (mode === "chunk") return t("runPage.scopeChunk");
  return t("runPage.answerWarning");
}

export function metricLabel(key: string, t: T): string {
  const labels: Record<string, string> = {
    "recall@1": t("runPage.metricRecall1"),
    "recall@5": t("runPage.metricRecall5"),
    "recall@10": t("runPage.metricRecall10"),
    mrr: t("runPage.metricMrr"),
    "ndcg@5": t("runPage.metricNdcg5"),
    "ndcg@10": t("runPage.metricNdcg10"),
    index_disk_mb: t("runPage.metricDisk"),
    index_ram_mb: t("runPage.metricMemory"),
  };
  return labels[key] ?? key;
}

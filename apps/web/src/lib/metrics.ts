/** Primary retrieval-quality keys shown prominently in the UI. */
export const PRIMARY_METRIC_KEYS = [
  "recall@1",
  "recall@5",
  "recall@10",
  "mrr",
  "ndcg@5",
  "ndcg@10",
] as const;

const HIDDEN_METRIC_KEYS = new Set([
  "cache_hit",
  "build_time_sec",
  "vector_count",
  "retrieval.mode",
  "quantization",
  "index_size_source",
  "by_query_type",
  "hnsw",
  "retrieve_k",
  // Failure stubs written by the orchestrator for a point that raised; they are
  // surfaced as an error banner, not as operational metrics.
  "status",
  "error",
]);

export function isPrimaryMetric(key: string): boolean {
  return (PRIMARY_METRIC_KEYS as readonly string[]).includes(key);
}

export function isHiddenMetric(key: string): boolean {
  return HIDDEN_METRIC_KEYS.has(key) || key.startsWith("by_");
}

export function isFailedRow(row: {
  metrics: Record<string, unknown> | undefined;
}): boolean {
  return row.metrics?.status === "failed";
}

export function rowError(row: {
  metrics: Record<string, unknown> | undefined;
}): string | null {
  const error = row.metrics?.error;
  return typeof error === "string" && error.trim() ? error : null;
}

export function formatMetricValue(value: unknown): string {
  if (typeof value === "number") return value.toFixed(3);
  if (value == null) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function recallFromMetrics(
  metrics: Record<string, unknown> | undefined,
): number | null {
  if (!metrics) return null;
  for (const key of ["recall@5", "recall@10", "recall@1"] as const) {
    const v = metrics[key];
    if (typeof v === "number") return v;
  }
  return null;
}

export function bestRowByRecall<T extends { metrics: Record<string, unknown> }>(
  rows: T[],
): T | null {
  let best: T | null = null;
  let bestScore = -1;
  for (const row of rows) {
    const score = recallFromMetrics(row.metrics);
    if (score != null && score > bestScore) {
      bestScore = score;
      best = row;
    }
  }
  return best;
}

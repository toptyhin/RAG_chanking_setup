/** Soft check: embedding vector dim below configured chunk length (different units). */

export function isEmbeddingDimBelowChunkSize(
  embeddingDimension: number | null | undefined,
  chunkSize: number | null | undefined,
): boolean {
  if (
    embeddingDimension == null ||
    chunkSize == null ||
    !Number.isFinite(embeddingDimension) ||
    !Number.isFinite(chunkSize)
  ) {
    return false;
  }
  return embeddingDimension > 0 && chunkSize > 0 && embeddingDimension < chunkSize;
}

/** Prefer dim of the model that will actually run, not a stale /current default. */
export function resolveEmbeddingDimensionForModel(
  modelId: string | null | undefined,
  loaded: Array<{ model_id: string; dimension: number }> | null | undefined,
  current?: { model_id: string; dimension: number } | null,
): number | null {
  const mid = modelId?.trim() ?? "";
  if (mid && loaded) {
    const row = loaded.find((item) => item.model_id === mid);
    if (row && typeof row.dimension === "number" && row.dimension > 0) {
      return row.dimension;
    }
  }
  if (current && mid && current.model_id === mid && current.dimension > 0) {
    return current.dimension;
  }
  if (!mid && current && current.dimension > 0) {
    return current.dimension;
  }
  return null;
}

function positiveNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) && value > 0
    ? value
    : null;
}

/** Measured max chunk length in chars from chunk_set artifact meta. */
export function maxCharsFromMeta(
  meta: Record<string, unknown> | null | undefined,
): number | null {
  if (!meta) return null;
  const length = meta.length_chars;
  if (length && typeof length === "object" && !Array.isArray(length)) {
    return positiveNumber((length as Record<string, unknown>).max_chars);
  }
  return positiveNumber(meta.max_chars);
}

/** Measured max approx-token length from chunk_set artifact meta. */
export function maxTokensFromMeta(
  meta: Record<string, unknown> | null | undefined,
): number | null {
  if (!meta) return null;
  const length = meta.length_chars;
  if (length && typeof length === "object" && !Array.isArray(length)) {
    return positiveNumber((length as Record<string, unknown>).max_tokens);
  }
  return positiveNumber(meta.max_tokens);
}

/**
 * Best-effort chunk length for embedding fit hints.
 * Prefer measured max chars from the ready set; fall back to configured limits.
 */
export function chunkSizeFromMeta(
  meta: Record<string, unknown> | null | undefined,
): number | null {
  const measured = maxCharsFromMeta(meta);
  if (measured != null) return measured;
  if (!meta) return null;
  for (const key of ["size", "chunk_size", "max_tokens"] as const) {
    const value = positiveNumber(meta[key]);
    if (value != null) return value;
  }
  const options = meta.options;
  if (options && typeof options === "object" && !Array.isArray(options)) {
    const nested = options as Record<string, unknown>;
    for (const key of ["size", "chunk_size", "max_tokens"] as const) {
      const value = positiveNumber(nested[key]);
      if (value != null) return value;
    }
  }
  return null;
}

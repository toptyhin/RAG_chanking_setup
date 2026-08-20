import type { TranslationKey } from "@/i18n";
import { interpolate } from "@/i18n";

const TYPE_PREFIX: Record<string, string> = {
  raw_bundle: "raw",
  clean_corpus: "clean",
  chunk_set: "chunks",
  test_set: "test",
  index_run: "index",
  experiment_run: "run",
  eval_report: "report",
};

export function shortId(id: string): string {
  if (id.length <= 16) return id;
  return `${id.slice(0, 8)}…${id.slice(-4)}`;
}

/** Display label: TYPE_source_document, e.g. raw_Устав_несения_службы */
export function artifactDisplayName(
  type: string,
  meta: Record<string, unknown> = {},
  id?: string,
): string {
  if (typeof meta.display_name === "string" && meta.display_name.trim()) {
    return meta.display_name.trim();
  }
  const prefix = TYPE_PREFIX[type] ?? type;
  if (typeof meta.source_name === "string" && meta.source_name.trim()) {
    return `${prefix}_${meta.source_name.trim()}`;
  }
  if (id) return shortId(id);
  return prefix;
}

export function formatBytes(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatWhen(
  iso: string | undefined,
  locale = "en-US",
): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(locale);
  } catch {
    return iso;
  }
}

type TranslateFn = (
  key: TranslationKey,
  vars?: Record<string, string | number>,
) => string;

export function artifactTypeLabel(type: string, t: TranslateFn): string {
  const keys: Record<string, TranslationKey> = {
    raw_bundle: "artifactTypes.rawBundle",
    clean_corpus: "artifactTypes.cleanCorpus",
    chunk_set: "artifactTypes.chunkSet",
    test_set: "artifactTypes.testSet",
    index_run: "artifactTypes.indexRun",
    experiment_run: "artifactTypes.experimentRun",
    eval_report: "artifactTypes.evalReport",
  };
  return keys[type] ? t(keys[type]) : type;
}

export function artifactSummary(
  meta: Record<string, unknown>,
  t?: TranslateFn,
): string | null {
  const label = (
    key: TranslationKey,
    count: number,
    fallback: string,
  ): string =>
    t ? t(key, { count }) : interpolate(fallback, { count });

  if (typeof meta.chunk_count === "number") {
    const base = label("format.chunks", meta.chunk_count, "{count} chunks");
    if (
      meta.chunk_count === 0 &&
      typeof meta.empty_reason === "string" &&
      meta.empty_reason.trim()
    ) {
      return `${base} — ${meta.empty_reason}`;
    }
    const length =
      meta.length_chars &&
      typeof meta.length_chars === "object" &&
      !Array.isArray(meta.length_chars)
        ? (meta.length_chars as Record<string, unknown>)
        : null;
    const maxChars =
      length && typeof length.max_chars === "number"
        ? length.max_chars
        : typeof meta.max_chars === "number"
          ? meta.max_chars
          : null;
    const maxTokens =
      length && typeof length.max_tokens === "number"
        ? length.max_tokens
        : null;
    if (maxChars != null && Number.isFinite(maxChars) && maxChars > 0) {
      if (
        t &&
        maxTokens != null &&
        Number.isFinite(maxTokens) &&
        maxTokens > 0
      ) {
        return `${base} · ${t("format.maxLength", {
          chars: maxChars,
          tokens: maxTokens,
        })}`;
      }
      return t
        ? `${base} · ${t("format.maxChars", { count: maxChars })}`
        : `${base} · max ${maxChars} chars`;
    }
    return base;
  }
  if (typeof meta.query_count === "number") {
    return label("format.queries", meta.query_count, "{count} queries");
  }
  if (typeof meta.document_count === "number") {
    return label("format.docs", meta.document_count, "{count} docs");
  }
  if (typeof meta.file_count === "number") {
    return label("format.files", meta.file_count, "{count} files");
  }
  return null;
}

/** True when a chunk_set artifact has at least one chunk. */
export function chunkSetHasChunks(meta: Record<string, unknown>): boolean {
  return typeof meta.chunk_count === "number" && meta.chunk_count > 0;
}

export function chunkSetEmptyReason(
  meta: Record<string, unknown>,
): string | null {
  if (chunkSetHasChunks(meta)) return null;
  if (typeof meta.empty_reason === "string" && meta.empty_reason.trim()) {
    return meta.empty_reason;
  }
  if (typeof meta.chunk_count === "number" && meta.chunk_count === 0) {
    return "0 chunks";
  }
  return null;
}

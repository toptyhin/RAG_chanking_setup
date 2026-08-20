import type { TranslationKey } from "@/i18n";
import {
  artifactDisplayName,
  chunkSetEmptyReason,
} from "@/lib/format";

type T = (key: TranslationKey, vars?: Record<string, string | number>) => string;

export function chunkingSummary(
  meta: Record<string, unknown>,
  t: T,
): string {
  const parts: string[] = [];
  const pipeline =
    typeof meta.chunk_pipeline_id === "string" ? meta.chunk_pipeline_id : null;
  if (pipeline) {
    parts.push(`${t("newRunPage.summaryPipeline")}: ${pipeline}`);
  }
  if (typeof meta.size === "number") {
    parts.push(`${t("newRunPage.summarySize")}: ${meta.size}`);
  }
  const length =
    meta.length_chars &&
    typeof meta.length_chars === "object" &&
    !Array.isArray(meta.length_chars)
      ? (meta.length_chars as Record<string, unknown>)
      : null;
  if (length && typeof length.max_chars === "number") {
    if (typeof length.max_tokens === "number") {
      parts.push(
        `${t("format.maxLength", {
          chars: length.max_chars,
          tokens: length.max_tokens,
        })}`,
      );
    } else {
      parts.push(`${t("newRunPage.summaryMaxChars")}: ${length.max_chars}`);
    }
  }
  if (typeof meta.overlap === "number") {
    parts.push(`${t("newRunPage.summaryOverlap")}: ${meta.overlap}`);
  }
  if (typeof meta.chunk_count === "number") {
    parts.push(`${t("newRunPage.summaryChunks")}: ${meta.chunk_count}`);
  }
  return parts.length > 0 ? parts.join(" · ") : "—";
}

export function formatAxisValue(value: unknown): string {
  if (Array.isArray(value)) return value.map(String).join(" / ");
  if (value == null) return "—";
  return String(value);
}

export function artifactLabel(
  a: { id: string; type: string; meta: Record<string, unknown> },
  kind: "chunk" | "test",
  t: T,
): string {
  const name = artifactDisplayName(a.type, a.meta, a.id);
  const n = kind === "chunk" ? a.meta.chunk_count : a.meta.query_count;
  const suffix =
    typeof n === "number"
      ? kind === "chunk"
        ? t("format.chunkSuffix", { count: n })
        : t("format.querySuffix", { count: n })
      : "";
  let base = `${name}${suffix}`;
  if (kind === "chunk") {
    const length =
      a.meta.length_chars &&
      typeof a.meta.length_chars === "object" &&
      !Array.isArray(a.meta.length_chars)
        ? (a.meta.length_chars as Record<string, unknown>)
        : null;
    if (length && typeof length.max_chars === "number") {
      if (typeof length.max_tokens === "number") {
        base = `${base} · ${t("format.maxLength", {
          chars: length.max_chars,
          tokens: length.max_tokens,
        })}`;
      } else {
        base = `${base} · ${t("format.maxChars", { count: length.max_chars })}`;
      }
    }
    const reason = chunkSetEmptyReason(a.meta);
    if (reason) return `${base} — ${reason}`;
  }
  return base;
}

export function presetTitle(
  id: Exclude<import("@/lib/presets").RunPresetId, "custom_topk">,
  t: T,
): string {
  return t(`presets.${id}.title` as TranslationKey);
}

export function presetDescription(
  id: Exclude<import("@/lib/presets").RunPresetId, "custom_topk">,
  t: T,
): string {
  return t(`presets.${id}.description` as TranslationKey);
}

export type LabMode = "prep" | "chunk" | "retrieval";

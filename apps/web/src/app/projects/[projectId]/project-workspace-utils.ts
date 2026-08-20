import type { Artifact, RelevantSpan } from "@/lib/types";
import type { TranslationKey } from "@/i18n";
import type { EvidenceLevel } from "@/lib/evidence-level";

export function byType(artifacts: Artifact[] | undefined, type: string): Artifact[] {
  return (artifacts ?? []).filter((a) => a.type === type);
}

/** Graded relevance: primary (2) vs secondary (1) for nDCG on L3/L4. */
export const GRADE_PRIMARY = 2;
export const GRADE_SECONDARY = 1;

export type QueryDraft = {
  text: string;
  relevant: string[];
  /** chunk_id → gain; only meaningful when level is L3/L4. */
  grades?: Record<string, number>;
  spans?: RelevantSpan[];
  evidenceQuotes?: string[];
  expectedAnswer?: string;
  sourceQuote?: string;
  level?: string;
  queryType?: string;
  source?: "synthetic" | "manual" | "imported";
};

export type DataPath = "byo" | "documents" | null;

export function defaultGradesFor(relevant: string[]): Record<string, number> {
  const grades: Record<string, number> = {};
  relevant.forEach((id, i) => {
    grades[id] = i === 0 ? GRADE_PRIMARY : GRADE_SECONDARY;
  });
  return grades;
}

export function evidenceTitleKey(level: EvidenceLevel): TranslationKey {
  if (level === "l3") return "projectPage.evidenceTitleL3";
  if (level === "l4") return "projectPage.evidenceTitleL4";
  return "projectPage.relevantChunks";
}

export function evidenceHintKey(level: EvidenceLevel): TranslationKey | null {
  if (level === "l3") return "projectPage.evidenceHintL3";
  if (level === "l4") return "projectPage.evidenceHintL4";
  if (level === "l1" || level === "l2") return "projectPage.evidenceHintL12";
  return null;
}

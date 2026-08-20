/** Helpers for L1–L4 evidence labeling in the question draft UI. */

export type EvidenceLevel = "l1" | "l2" | "l3" | "l4" | "other";

export function evidenceLevelOf(
  level?: string | null,
  queryType?: string | null,
): EvidenceLevel {
  const raw = (queryType || level || "").trim().toLowerCase().replace(/_/g, "-");
  if (raw === "l1" || raw.startsWith("l1")) return "l1";
  if (raw === "l2" || raw.startsWith("l2")) return "l2";
  if (raw === "l3" || raw.startsWith("l3")) return "l3";
  if (raw === "l4" || raw.startsWith("l4")) return "l4";
  return "other";
}

export function needsEvidenceReview(level: EvidenceLevel): boolean {
  return level === "l3" || level === "l4";
}

export function minEvidenceChunks(level: EvidenceLevel): number {
  if (level === "l3") return 2;
  if (level === "l4") return 1;
  return 1;
}

export type EvidenceIssue = {
  questionIndex: number;
  code: "need_chunks" | "need_two" | "l4_single";
};

export function validateEvidenceDraft(
  queries: {
    text: string;
    relevant: string[];
    level?: string;
    queryType?: string;
  }[],
): EvidenceIssue[] {
  const issues: EvidenceIssue[] = [];
  queries.forEach((q, questionIndex) => {
    if (!q.text.trim()) return;
    const level = evidenceLevelOf(q.level, q.queryType);
    const n = q.relevant.length;
    if (n < 1) {
      issues.push({ questionIndex, code: "need_chunks" });
      return;
    }
    if (level === "l3" && n < 2) {
      issues.push({ questionIndex, code: "need_two" });
    }
  });
  return issues;
}

/** Soft warnings that do not block save. */
export function evidenceWarnings(
  queries: {
    text: string;
    relevant: string[];
    level?: string;
    queryType?: string;
  }[],
): EvidenceIssue[] {
  const warnings: EvidenceIssue[] = [];
  queries.forEach((q, questionIndex) => {
    if (!q.text.trim()) return;
    const level = evidenceLevelOf(q.level, q.queryType);
    if (level === "l4" && q.relevant.length === 1) {
      warnings.push({ questionIndex, code: "l4_single" });
    }
  });
  return warnings;
}

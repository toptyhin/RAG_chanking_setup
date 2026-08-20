import type { TranslationKey } from "@/i18n";
import type { ChunkContent, EvidenceCandidate, RelevantSpan } from "@/lib/types";

export const GRADE_PRIMARY = 2;
export const GRADE_SECONDARY = 1;

export type EvidencePickerProps = {
  projectId: string;
  chunkSetId: string;
  cleanCorpusId?: string | null;
  question: string;
  expectedAnswer?: string;
  sourceQuote?: string;
  evidenceQuotes?: string[];
  queryType?: string;
  level?: string;
  review: boolean;
  relevant: string[];
  grades?: Record<string, number>;
  spans?: RelevantSpan[];
  allChunks: ChunkContent[];
  onChange: (next: {
    relevant: string[];
    grades?: Record<string, number>;
    spans?: RelevantSpan[];
  }) => void;
};

export function evidenceReasonKey(reason: string): TranslationKey {
  if (reason === "quote") return "projectPage.evidenceReasonQuote";
  if (reason === "bm25") return "projectPage.evidenceReasonBm25";
  if (reason === "neighbor") return "projectPage.evidenceReasonNeighbor";
  return "projectPage.evidenceReasonBm25";
}

export function buildPinnedCandidates(
  relevant: string[],
  candidates: EvidenceCandidate[],
  chunkById: Map<string, ChunkContent>,
): EvidenceCandidate[] {
  return relevant.flatMap((id) => {
    const fromCand = candidates.find((c) => c.chunk_id === id);
    const fromAll = chunkById.get(id);
    if (fromCand) return [fromCand];
    if (fromAll) {
      return [
        {
          chunk_id: fromAll.chunk_id,
          doc_id: fromAll.doc_id,
          text: fromAll.text,
          start_char: fromAll.start_char ?? null,
          end_char: fromAll.end_char ?? null,
          score: 0,
          reason: "pinned",
        } satisfies EvidenceCandidate,
      ];
    }
    return [];
  });
}

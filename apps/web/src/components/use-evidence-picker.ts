import { useEffect, useMemo, useState } from "react";
import { fetchEvidenceCandidates } from "@/lib/api";
import type { ChunkContent, EvidenceCandidate, RelevantSpan } from "@/lib/types";
import { useI18n } from "@/lib/locale";
import {
  buildPinnedCandidates,
  GRADE_PRIMARY,
  GRADE_SECONDARY,
  type EvidencePickerProps,
} from "@/components/evidence-picker-types";

export function useEvidencePicker({
  projectId,
  chunkSetId,
  cleanCorpusId,
  question,
  expectedAnswer,
  sourceQuote,
  evidenceQuotes,
  queryType,
  review,
  relevant,
  grades,
  spans,
  allChunks,
  onChange,
}: EvidencePickerProps) {
  const { t } = useI18n();
  const [candidates, setCandidates] = useState<EvidenceCandidate[]>([]);
  const [quoteSpans, setQuoteSpans] = useState<RelevantSpan[]>(spans ?? []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const chunkById = useMemo(() => {
    const m = new Map<string, ChunkContent>();
    for (const c of allChunks) m.set(c.chunk_id, c);
    return m;
  }, [allChunks]);

  const relevantSet = useMemo(() => new Set(relevant), [relevant]);

  useEffect(() => {
    let cancelled = false;

    async function loadCandidates() {
      if (!chunkSetId || !question.trim()) {
        if (!cancelled) setCandidates([]);
        return;
      }
      if (!cancelled) {
        setLoading(true);
        setError(null);
      }
      try {
        const res = await fetchEvidenceCandidates(projectId, {
          chunk_set_id: chunkSetId,
          clean_corpus_id: cleanCorpusId || undefined,
          question: question.trim(),
          expected_answer: expectedAnswer,
          source_quote: sourceQuote,
          evidence_quotes: evidenceQuotes,
          query_type: queryType,
          limit: 30,
        });
        if (cancelled) return;
        setCandidates(res.candidates);
        setQuoteSpans(res.quote_spans ?? []);
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof Error
            ? err.message
            : t("projectPage.evidenceCandidatesError"),
        );
        setCandidates([]);
      } finally {
        setLoading(false);
      }
    }

    void loadCandidates();
    return () => {
      cancelled = true;
      setLoading(false);
    };
  }, [
    projectId,
    chunkSetId,
    cleanCorpusId,
    question,
    expectedAnswer,
    sourceQuote,
    evidenceQuotes,
    queryType,
    t,
  ]);

  async function reloadCandidates() {
    if (!chunkSetId || !question.trim()) {
      setCandidates([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetchEvidenceCandidates(projectId, {
        chunk_set_id: chunkSetId,
        clean_corpus_id: cleanCorpusId || undefined,
        question: question.trim(),
        expected_answer: expectedAnswer,
        source_quote: sourceQuote,
        evidence_quotes: evidenceQuotes,
        query_type: queryType,
        limit: 30,
      });
      setCandidates(res.candidates);
      setQuoteSpans(res.quote_spans ?? []);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : t("projectPage.evidenceCandidatesError"),
      );
      setCandidates([]);
    } finally {
      setLoading(false);
    }
  }

  function toggleChunk(c: {
    chunk_id: string;
    doc_id?: string;
    start_char?: number | null;
    end_char?: number | null;
  }) {
    const checked = relevantSet.has(c.chunk_id);
    if (checked) {
      const nextRelevant = relevant.filter((id) => id !== c.chunk_id);
      const nextGrades = { ...(grades ?? {}) };
      delete nextGrades[c.chunk_id];
      const nextSpans = (spans ?? quoteSpans).filter((s) => {
        if (
          c.start_char == null ||
          c.end_char == null ||
          !c.doc_id ||
          s.doc_id !== c.doc_id
        ) {
          return true;
        }
        return !(s.start === c.start_char && s.end === c.end_char);
      });
      onChange({
        relevant: nextRelevant,
        grades: review ? nextGrades : undefined,
        spans: nextSpans,
      });
      return;
    }
    const nextRelevant = [...relevant, c.chunk_id];
    const nextGrades = review
      ? {
          ...(grades ?? {}),
          [c.chunk_id]:
            nextRelevant.length === 1 ? GRADE_PRIMARY : GRADE_SECONDARY,
        }
      : undefined;
    let nextSpans = [...(spans ?? quoteSpans)];
    if (
      c.doc_id &&
      c.start_char != null &&
      c.end_char != null &&
      !nextSpans.some(
        (s) =>
          s.doc_id === c.doc_id &&
          s.start === c.start_char &&
          s.end === c.end_char,
      )
    ) {
      nextSpans = [
        ...nextSpans,
        { doc_id: c.doc_id, start: c.start_char, end: c.end_char },
      ];
    }
    onChange({
      relevant: nextRelevant,
      grades: nextGrades,
      spans: nextSpans,
    });
  }

  function toggleGrade(chunkId: string, isPrimary: boolean) {
    onChange({
      relevant,
      grades: {
        ...(grades ?? {}),
        [chunkId]: isPrimary ? GRADE_SECONDARY : GRADE_PRIMARY,
      },
      spans: spans ?? quoteSpans,
    });
  }

  const pinned = buildPinnedCandidates(relevant, candidates, chunkById);
  const suggested = candidates.filter((c) => !relevantSet.has(c.chunk_id));

  const searchHits = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return [];
    return allChunks
      .filter(
        (c) =>
          c.chunk_id.toLowerCase().includes(needle) ||
          c.text.toLowerCase().includes(needle),
      )
      .slice(0, 40);
  }, [allChunks, search]);

  return {
    t,
    loading,
    error,
    loadCandidates: reloadCandidates,
    pinned,
    suggested,
    search,
    setSearch,
    showSearch,
    setShowSearch,
    expanded,
    setExpanded,
    relevant,
    grades,
    review,
    toggleChunk,
    toggleGrade,
    searchHits,
  };
}

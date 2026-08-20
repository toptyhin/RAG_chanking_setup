"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useParams, usePathname, useRouter } from "next/navigation";
import {
  estimatePrepareQuestions,
  getChunkSetContent,
  getLlmConfig,
  getProject,
  getTestSetContent,
  importByoChunks,
  importTestSet,
  listArtifacts,
  listExperiments,
  prepareTestSetQuestions,
  uploadRawBundle,
} from "@/lib/api";
import type { Artifact, ChunkContent, RelevantSpan, TestSetContent } from "@/lib/types";
import {
  artifactDisplayName,
  artifactSummary,
  chunkSetHasChunks,
} from "@/lib/format";
import {
  evidenceLevelOf,
  evidenceWarnings,
  needsEvidenceReview,
  validateEvidenceDraft,
} from "@/lib/evidence-level";
import { resolveQueryType } from "@/lib/query-type";
import { useI18n } from "@/lib/locale";
import { SAMPLE_CHUNKS, sampleTestSet } from "@/lib/samples";
import type { ProjectStage } from "@/components/project-nav";
import {
  byType,
  defaultGradesFor,
  GRADE_PRIMARY,
  GRADE_SECONDARY,
  type DataPath,
  type QueryDraft,
} from "./project-workspace-utils";

export function useProjectWorkspace(initialStage: ProjectStage) {
  const { t } = useI18n();
  const params = useParams<{ projectId: string }>();
  const projectId = params.projectId;
  const pathname = usePathname();
  const router = useRouter();
  const qc = useQueryClient();
  const activeTab = initialStage;

  function setActiveTab(tab: ProjectStage) {
    const paths: Record<ProjectStage, string> = {
      overview: `/projects/${projectId}`,
      data: `/projects/${projectId}/data`,
      test: `/projects/${projectId}/test-set`,
      labs: `/projects/${projectId}/labs`,
      results: `/projects/${projectId}/results`,
    };
    router.push(paths[tab]);
  }

  function artifactLabel(a: Artifact): string {
    const name = artifactDisplayName(a.type, a.meta, a.id);
    const summary = artifactSummary(a.meta, t);
    return summary ? `${name} · ${summary}` : name;
  }

  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });

  const artifacts = useQuery({
    queryKey: ["artifacts", projectId],
    queryFn: () => listArtifacts(projectId),
  });

  const experiments = useQuery({
    queryKey: ["experiments", projectId],
    queryFn: () => listExperiments(projectId),
  });

  const cleanCorpora = useMemo(
    () => byType(artifacts.data, "clean_corpus"),
    [artifacts.data],
  );
  const rawBundles = useMemo(
    () => byType(artifacts.data, "raw_bundle"),
    [artifacts.data],
  );
  const chunkSets = useMemo(
    () => byType(artifacts.data, "chunk_set"),
    [artifacts.data],
  );
  const usableChunkSets = useMemo(
    () => chunkSets.filter((a) => chunkSetHasChunks(a.meta)),
    [chunkSets],
  );
  const emptyChunkSets = useMemo(
    () => chunkSets.filter((a) => !chunkSetHasChunks(a.meta)),
    [chunkSets],
  );
  const totalChunks = useMemo(
    () =>
      usableChunkSets.reduce((sum, a) => {
        const n = a.meta.chunk_count;
        return sum + (typeof n === "number" ? n : 0);
      }, 0),
    [usableChunkSets],
  );
  const testSets = useMemo(
    () => byType(artifacts.data, "test_set"),
    [artifacts.data],
  );

  const hasChunks = usableChunkSets.length > 0;
  const hasTestSet = testSets.length > 0;
  const ready = hasChunks && hasTestSet;
  const anyLabReady =
    hasTestSet &&
    (rawBundles.length > 0 || cleanCorpora.length > 0 || hasChunks);

  const [dataPath, setDataPath] = useState<DataPath>(null);

  const [cleanId, setCleanId] = useState("");
  const [byoJson, setByoJson] = useState(() =>
    JSON.stringify(SAMPLE_CHUNKS, null, 2),
  );

  const [labelChunkSetId, setLabelChunkSetId] = useState("");
  const [labelCleanCorpusId, setLabelCleanCorpusId] = useState("");
  const [queries, setQueries] = useState<QueryDraft[]>([]);
  const [showManualEditor, setShowManualEditor] = useState(false);
  const [draftOpen, setDraftOpen] = useState(false);
  const [chunkPreview, setChunkPreview] = useState<ChunkContent[]>([]);
  const [chunkLoadError, setChunkLoadError] = useState<string | null>(null);

  async function refreshAll() {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["artifacts", projectId] }),
      qc.invalidateQueries({ queryKey: ["experiments", projectId] }),
    ]);
  }

  const upload = useMutation({
    mutationFn: (files: File[]) => {
      if (!files.length) throw new Error(t("projectPage.selectFiles"));
      return uploadRawBundle(projectId, files);
    },
    onSuccess: async (data) => {
      setCleanId(data.clean_corpus.id);
      await refreshAll();
    },
  });

  const byo = useMutation({
    mutationFn: () => importByoChunks(projectId, JSON.parse(byoJson)),
    onSuccess: async (data) => {
      await refreshAll();
      setLabelChunkSetId(data.artifact.id);
      setDataPath(null);
    },
  });

  const sample = useMutation({
    mutationFn: async () => {
      const chunks = await importByoChunks(projectId, SAMPLE_CHUNKS);
      const test = await importTestSet(
        projectId,
        sampleTestSet(chunks.artifact.id),
      );
      return { chunks, test };
    },
    onSuccess: async (data) => {
      await refreshAll();
      setLabelChunkSetId(data.chunks.artifact.id);
      setDataPath(null);
    },
  });

  const testImport = useMutation({
    mutationFn: () => {
      const chunkSetId = labelChunkSetId || chunkSets[0]?.id;
      if (!chunkSetId) throw new Error(t("projectPage.selectChunkSet"));
      const blocking = validateEvidenceDraft(queries);
      if (blocking.length > 0) {
        const first = blocking[0];
        if (first.code === "need_two") {
          throw new Error(
            t("projectPage.evidenceNeedTwo", { n: first.questionIndex + 1 }),
          );
        }
        throw new Error(t("projectPage.eachNeedsChunk"));
      }
      const soft = evidenceWarnings(queries);
      if (soft.some((w) => w.code === "l4_single")) {
        const ok = window.confirm(t("projectPage.evidenceL4SingleConfirm"));
        if (!ok) throw new Error(t("projectPage.evidenceSaveCancelled"));
      }
      const chunkPreviewById = new Map(
        chunkPreview.map((chunk) => [chunk.chunk_id, chunk]),
      );
      const cleaned = [];
      for (const q of queries) {
        const meta: Record<string, string> = {};
        if (q.level) meta.level = q.level;
        const queryType = resolveQueryType({
          queryType: q.queryType,
          level: q.level,
          meta,
        });
        const level = evidenceLevelOf(q.level, q.queryType);
        const grades =
          needsEvidenceReview(level) && q.relevant.length > 0
            ? Object.fromEntries(
                q.relevant.map((id) => [
                  id,
                  q.grades?.[id] ??
                    (q.relevant[0] === id ? GRADE_PRIMARY : GRADE_SECONDARY),
                ]),
              )
            : undefined;
        let spans = q.spans ?? [];
        if (spans.length === 0 && q.relevant.length > 0) {
          const derived: RelevantSpan[] = [];
          for (const id of q.relevant) {
            const c = chunkPreviewById.get(id);
            if (
              c &&
              c.doc_id &&
              typeof c.start_char === "number" &&
              typeof c.end_char === "number"
            ) {
              derived.push({
                doc_id: c.doc_id,
                start: c.start_char,
                end: c.end_char,
              });
            }
          }
          spans = derived;
        }
        const text = q.text.trim();
        if (text.length === 0) continue;
        cleaned.push({
          text,
          relevant_chunk_ids: q.relevant,
          relevant_spans: spans,
          relevance_grades: grades,
          expected_answer: q.expectedAnswer?.trim() || undefined,
          source_quote: q.sourceQuote?.trim() || undefined,
          query_type: queryType,
          source: q.source ?? "manual",
          reviewed: true,
          label_status: "verified",
          meta: {
            ...meta,
            source: q.source ?? "manual",
            reviewed: true,
            label_status: "verified",
          },
        });
      }
      if (cleaned.length === 0) {
        throw new Error(t("projectPage.addQuestionWithText"));
      }
      return importTestSet(projectId, {
        chunk_set_id: chunkSetId,
        source: cleaned.every((query) => query.source === "synthetic")
          ? "synthetic"
          : "manual",
        reviewed: true,
        queries: cleaned,
      });
    },
    onSuccess: async () => {
      setQueries([]);
      setShowManualEditor(false);
      setDraftOpen(false);
      await refreshAll();
      await qc.invalidateQueries({
        queryKey: ["test-set-contents", projectId],
      });
    },
  });

  const testSetIdsKey = useMemo(
    () => testSets.map((a) => a.id).join(","),
    [testSets],
  );

  const readyTestQuestions = useQuery({
    queryKey: ["test-set-contents", projectId, testSetIdsKey],
    queryFn: async () => {
      const knownChunkSetIds = new Set(chunkSets.map((a) => a.id));
      const rows = await Promise.all(
        testSets.map(async (artifact) => {
          const content = await getTestSetContent(artifact.id);
          return { artifact, content };
        }),
      );

      const chunkTextById = new Map<string, string>();
      const chunkSetIdsToLoad = new Set<string>();

      for (const { artifact, content } of rows) {
        const metaChunk =
          typeof artifact.meta.chunk_set_id === "string"
            ? artifact.meta.chunk_set_id
            : typeof content.meta?.chunk_set_id === "string"
              ? content.meta.chunk_set_id
              : null;
        const parentCandidates = [
          ...(metaChunk ? [metaChunk] : []),
          ...(content.parent_ids ?? []),
          ...artifact.parent_ids,
        ];
        const chunkSetId =
          parentCandidates.find((id) => knownChunkSetIds.has(id)) ??
          parentCandidates[0] ??
          null;

        if (chunkSetId) {
          chunkSetIdsToLoad.add(chunkSetId);
        }
      }

      await Promise.all(
        [...chunkSetIdsToLoad].map(async (chunkSetId) => {
          try {
            const cs = await getChunkSetContent(chunkSetId);
            for (const c of cs.chunks ?? []) {
              chunkTextById.set(c.chunk_id, c.text);
            }
          } catch {
            // Preview optional — questions still render without texts.
          }
        }),
      );
      return {
        rows,
        chunkTextById: Object.fromEntries(chunkTextById),
      };
    },
    enabled: testSets.length > 0 && activeTab === "test",
  });

  const testQuality = useMemo(() => {
    const allQueries = (readyTestQuestions.data?.rows ?? []).flatMap(
      ({ content }) => content.queries ?? [],
    );
    const reviewed = allQueries.filter(
      (q) =>
        q.label_status === "verified" || q.meta?.label_status === "verified",
    ).length;
    const levels = new Set<string>();
    const sources = new Set<string>();
    for (const q of allQueries) {
      if (typeof q.meta?.level === "string") {
        levels.add(q.meta.level.toLowerCase());
      }
      const source = q.source ?? q.meta?.source;
      if (typeof source === "string") {
        sources.add(source);
      }
    }
    return {
      total: allQueries.length,
      reviewed,
      levels: levels.size,
      source:
        sources.size === 1
          ? Array.from(sources)[0]
          : sources.size > 1
            ? "mixed"
            : "unknown",
    };
  }, [readyTestQuestions.data]);

  const llmConfig = useQuery({
    queryKey: ["llm", "config"],
    queryFn: getLlmConfig,
  });

  function resolveCleanCorpusForChunkSet(
    chunkSetId: string | undefined,
  ): string | null {
    if (!chunkSetId) return null;
    const chunkSet = usableChunkSets.find((a) => a.id === chunkSetId);
    if (!chunkSet) return null;
    const parentClean = chunkSet.parent_ids.find((pid) =>
      cleanCorpora.some((c) => c.id === pid),
    );
    return parentClean ?? null;
  }

  const prepareCleanCorpusId = useMemo(() => {
    const chunkSetId = labelChunkSetId || usableChunkSets[0]?.id;
    const fromChunkSet = (() => {
      if (!chunkSetId) return null;
      const chunkSet = usableChunkSets.find((a) => a.id === chunkSetId);
      if (!chunkSet) return null;
      const parentClean = chunkSet.parent_ids.find((pid) =>
        cleanCorpora.some((c) => c.id === pid),
      );
      return parentClean ?? null;
    })();
    return (
      labelCleanCorpusId || fromChunkSet || cleanCorpora[0]?.id || ""
    );
  }, [labelCleanCorpusId, labelChunkSetId, usableChunkSets, cleanCorpora]);

  const prepareEstimate = useQuery({
    queryKey: [
      "prepare-estimate",
      projectId,
      prepareCleanCorpusId,
      llmConfig.data?.provider,
      llmConfig.data?.ollama.model,
      llmConfig.data?.openrouter.model,
      llmConfig.data?.gigachat.model,
    ],
    queryFn: () =>
      estimatePrepareQuestions(projectId, {
        clean_corpus_id: prepareCleanCorpusId,
      }),
    enabled: Boolean(prepareCleanCorpusId) && activeTab === "test",
  });

  const prepareQuestions = useMutation({
    mutationFn: async () => {
      const chunkSetId = labelChunkSetId || usableChunkSets[0]?.id;
      const cleanIdForPrep = prepareCleanCorpusId;
      if (!cleanIdForPrep) {
        throw new Error(t("projectPage.needCleanCorpusForPrep"));
      }
      if (chunkSetId && chunkPreview.length === 0) {
        await loadChunksForLabels(chunkSetId);
      }
      const hasDraft = queries.some((q) => q.text.trim().length > 0);
      if (
        hasDraft &&
        !window.confirm(t("projectPage.prepareOverwriteConfirm"))
      ) {
        return null;
      }
      return prepareTestSetQuestions(projectId, {
        clean_corpus_id: cleanIdForPrep,
        chunk_set_id: chunkSetId || undefined,
      });
    },
    onSuccess: (data) => {
      if (!data) return;
      setQueries(
        data.questions.map((q) => {
          const level = evidenceLevelOf(
            q.level,
            q.query_type ?? resolveQueryType({ level: q.level }),
          );
          const relevant = q.relevant_chunk_ids ?? [];
          return {
            text: q.text,
            relevant,
            grades: needsEvidenceReview(level)
              ? defaultGradesFor(relevant)
              : undefined,
            spans: q.relevant_spans ?? [],
            evidenceQuotes: q.evidence_quotes ?? undefined,
            expectedAnswer: q.expected_answer ?? undefined,
            sourceQuote: q.source_quote ?? undefined,
            level: q.level ?? undefined,
            queryType:
              q.query_type ??
              resolveQueryType({ level: q.level }) ??
              undefined,
            source: "synthetic",
          };
        }),
      );
      setShowManualEditor(false);
      setDraftOpen(false);
      void qc.invalidateQueries({
        queryKey: ["prepare-estimate", projectId],
      });
    },
  });

  const llmModelLabel = useMemo(() => {
    const cfg = llmConfig.data;
    if (!cfg) return null;
    const model =
      cfg.provider === "ollama"
        ? cfg.ollama.model
        : cfg.provider === "openrouter"
          ? cfg.openrouter.model
          : cfg.gigachat.model;
    return `${cfg.provider} / ${model}`;
  }, [llmConfig.data]);

  async function loadChunksForLabels(chunkSetId: string) {
    setLabelChunkSetId(chunkSetId);
    setChunkLoadError(null);
    const linkedClean = resolveCleanCorpusForChunkSet(chunkSetId);
    if (linkedClean) {
      setLabelCleanCorpusId(linkedClean);
    }
    if (!chunkSetId) {
      setChunkPreview([]);
      return;
    }
    try {
      const content = await getChunkSetContent(chunkSetId);
      setChunkPreview(content.chunks ?? []);
    } catch (err) {
      setChunkPreview([]);
      setChunkLoadError(
        err instanceof Error ? err.message : t("projectPage.failedLoadChunks"),
      );
    }
  }

  useEffect(() => {
    if (activeTab !== "test") return;
    const id = labelChunkSetId || usableChunkSets[0]?.id;
    if (!id || chunkPreview.length > 0) return;

    let cancelled = false;
    setLabelChunkSetId(id);
    setChunkLoadError(null);
    const chunkSet = usableChunkSets.find((a) => a.id === id);
    const linkedClean = chunkSet
      ? (chunkSet.parent_ids.find((pid) =>
          cleanCorpora.some((c) => c.id === pid),
        ) ?? null)
      : null;
    if (linkedClean) {
      setLabelCleanCorpusId(linkedClean);
    }

    void (async () => {
      try {
        const content = await getChunkSetContent(id);
        if (cancelled) return;
        setChunkPreview(content.chunks ?? []);
      } catch (err) {
        if (cancelled) return;
        setChunkPreview([]);
        setChunkLoadError(
          err instanceof Error ? err.message : t("projectPage.failedLoadChunks"),
        );
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    activeTab,
    labelChunkSetId,
    usableChunkSets,
    cleanCorpora,
    chunkPreview.length,
    t,
  ]);

  return {
    projectId,
    pathname,
    activeTab,
    setActiveTab,
    artifactLabel,
    project,
    experiments,
    totalChunks,
    testSets,
    hasChunks,
    hasTestSet,
    ready,
    anyLabReady,
    rawBundles,
    cleanCorpora,
    chunkSets,
    usableChunkSets,
    emptyChunkSets,
    dataPath,
    setDataPath,
    cleanId,
    setCleanId,
    byoJson,
    setByoJson,
    labelChunkSetId,
    labelCleanCorpusId,
    setLabelCleanCorpusId,
    queries,
    setQueries,
    showManualEditor,
    setShowManualEditor,
    draftOpen,
    setDraftOpen,
    chunkPreview,
    chunkLoadError,
    refreshAll,
    upload,
    byo,
    sample,
    testImport,
    readyTestQuestions,
    testQuality,
    prepareCleanCorpusId,
    prepareEstimate,
    prepareQuestions,
    llmModelLabel,
    loadChunksForLabels,
  };
}

export type ProjectWorkspaceState = ReturnType<typeof useProjectWorkspace>;

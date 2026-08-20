"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import {
  createExperiment,
  getCurrentEmbedding,
  getCurrentRerank,
  getEmbeddingConfig,
  getProject,
  listArtifacts,
  listLoadedEmbeddings,
  previewChunkSet,
} from "@/lib/api";
import { resolveEmbeddingDimensionForModel } from "@/lib/chunk-embedding-fit";
import { activeEmbeddingModelId } from "@/lib/embedding";
import { useI18n } from "@/lib/locale";
import {
  RUN_PRESETS,
  applyQuantizationChoice,
  type QuantizationChoice,
  type RunPresetId,
} from "@/lib/presets";
import { chunkSetHasChunks } from "@/lib/format";
import type { Artifact } from "@/lib/types";
import { formatAxisValue, type LabMode } from "./new-run-utils";

export function useNewRunForm(projectId: string) {
  const { t } = useI18n();
  const router = useRouter();
  const qc = useQueryClient();

  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });

  const artifacts = useQuery({
    queryKey: ["artifacts", projectId],
    queryFn: () => listArtifacts(projectId),
  });

  const embeddingConfig = useQuery({
    queryKey: ["embedding", "config"],
    queryFn: getEmbeddingConfig,
  });

  const currentEmbedding = useQuery({
    queryKey: ["models", "embedding", "current"],
    queryFn: getCurrentEmbedding,
  });

  const loadedEmbeddings = useQuery({
    queryKey: ["models", "embedding", "loaded"],
    queryFn: listLoadedEmbeddings,
  });

  const currentRerank = useQuery({
    queryKey: ["models", "rerank", "current"],
    queryFn: getCurrentRerank,
  });

  const allChunkSets = useMemo(
    () => (artifacts.data ?? []).filter((a) => a.type === "chunk_set"),
    [artifacts.data],
  );
  const chunkSets = useMemo(
    () => allChunkSets.filter((a) => chunkSetHasChunks(a.meta)),
    [allChunkSets],
  );
  const emptyChunkSets = useMemo(
    () => allChunkSets.filter((a) => !chunkSetHasChunks(a.meta)),
    [allChunkSets],
  );
  const testSets = useMemo(
    () => (artifacts.data ?? []).filter((a) => a.type === "test_set"),
    [artifacts.data],
  );
  const rawBundles = useMemo(
    () => (artifacts.data ?? []).filter((a) => a.type === "raw_bundle"),
    [artifacts.data],
  );
  const cleanCorpora = useMemo(
    () => (artifacts.data ?? []).filter((a) => a.type === "clean_corpus"),
    [artifacts.data],
  );

  const [labMode, setLabMode] = useState<LabMode>("retrieval");
  const [chunkSetId, setChunkSetId] = useState("");
  const [rawBundleId, setRawBundleId] = useState("");
  const [cleanCorpusId, setCleanCorpusId] = useState("");
  const [testSetId, setTestSetId] = useState("");
  const [presetId, setPresetId] = useState<RunPresetId>("quick");
  const [customTopK, setCustomTopK] = useState("5");
  const [enableRerank, setEnableRerank] = useState(false);
  const [embeddingModelOverride, setEmbeddingModelOverride] = useState("");
  const [quantization, setQuantization] = useState<QuantizationChoice>("none");

  const hasStartArtifact =
    labMode === "prep"
      ? rawBundles.length > 0
      : labMode === "chunk"
        ? cleanCorpora.length > 0
        : chunkSets.length > 0;
  const ready = hasStartArtifact && testSets.length > 0;
  const selectedPreset = RUN_PRESETS.find((p) => p.id === presetId);

  const selectedChunkSet: Artifact | undefined = useMemo(() => {
    const id = chunkSetId || chunkSets[0]?.id;
    return chunkSets.find((a) => a.id === id);
  }, [chunkSetId, chunkSets]);

  const selectedCleanCorpusId = cleanCorpusId || cleanCorpora[0]?.id || "";

  const chunkLabPreview = useMutation({
    mutationFn: async () => {
      if (!selectedCleanCorpusId) {
        throw new Error(t("newRunPage.needCleanCorpus"));
      }
      const preview = await previewChunkSet(projectId, {
        clean_corpus_id: selectedCleanCorpusId,
        provider: "reference_fixed",
        size: 512,
        overlap: 64,
        preview_count: 5,
      });
      return { preview, cleanCorpusId: selectedCleanCorpusId };
    },
  });

  const chunkLabPreviewFresh =
    chunkLabPreview.data?.cleanCorpusId === selectedCleanCorpusId;

  const embeddingModelId = useMemo(() => {
    const fromConfig = activeEmbeddingModelId(embeddingConfig.data);
    if (fromConfig) return fromConfig;
    return currentEmbedding.data?.model_id ?? "";
  }, [embeddingConfig.data, currentEmbedding.data?.model_id]);

  const modelForRun = useMemo(
    () => embeddingModelOverride.trim() || embeddingModelId.trim(),
    [embeddingModelOverride, embeddingModelId],
  );

  const embeddingDimensionForRun = useMemo(
    () =>
      resolveEmbeddingDimensionForModel(
        modelForRun,
        loadedEmbeddings.data,
        currentEmbedding.data,
      ),
    [modelForRun, loadedEmbeddings.data, currentEmbedding.data],
  );

  const rerankModelId =
    currentRerank.data?.model_id ??
    currentRerank.data?.default_model ??
    "cross-encoder/ms-marco-MiniLM-L-6-v2";

  const qdrantSummary = useMemo(() => {
    let fixed: Record<string, unknown> = {};
    let swept: Record<string, unknown[]> = {};
    if (presetId === "custom_topk") {
      fixed = {
        "retrieval.mode": "dense",
        "retrieval.top_k": Number(customTopK) || 5,
      };
    } else if (selectedPreset) {
      fixed = { ...selectedPreset.fixed };
      swept = { ...selectedPreset.swept };
    }
    ({ fixed, swept } = applyQuantizationChoice(fixed, swept, quantization));
    const mode = swept["retrieval.mode"] ?? fixed["retrieval.mode"] ?? "dense";
    const topK = swept["retrieval.top_k"] ?? fixed["retrieval.top_k"] ?? "—";
    const quant =
      swept.quantization ??
      fixed.quantization ??
      fixed["index.quantization"] ??
      null;
    const hnsw =
      fixed["index.hnsw"] ??
      (fixed["index.hnsw.m"] != null || fixed["index.hnsw.ef_construct"] != null
        ? {
            m: fixed["index.hnsw.m"],
            ef_construct: fixed["index.hnsw.ef_construct"],
          }
        : null);

    const parts = [
      `${t("newRunPage.summaryMode")}: ${formatAxisValue(mode)}`,
      `${t("newRunPage.summaryTopK")}: ${formatAxisValue(topK)}`,
      `${t("newRunPage.summaryQuantization")}: ${
        quant == null ? t("newRunPage.summaryNone") : formatAxisValue(quant)
      }`,
      `${t("newRunPage.summaryHnsw")}: ${
        hnsw == null ? t("newRunPage.summaryDefault") : formatAxisValue(hnsw)
      }`,
    ];
    return parts.join(" · ");
  }, [presetId, customTopK, selectedPreset, quantization, t]);

  const configCount = useMemo(() => {
    if (labMode === "prep") return 2;
    if (labMode === "chunk") return 3;
    let swept =
      presetId === "custom_topk" || !selectedPreset ? {} : { ...selectedPreset.swept };
    let fixed =
      presetId === "custom_topk"
        ? { "retrieval.mode": "dense", "retrieval.top_k": Number(customTopK) || 5 }
        : { ...(selectedPreset?.fixed ?? {}) };
    ({ fixed, swept } = applyQuantizationChoice(fixed, swept, quantization));
    const values = Object.values(swept);
    return values.length === 0
      ? 1
      : values.reduce((total, axis) => total * Math.max(axis.length, 1), 1);
  }, [labMode, presetId, selectedPreset, customTopK, quantization]);

  const fixedAxes =
    labMode === "prep"
      ? "chunk.size, retrieval.top_k"
      : labMode === "chunk"
        ? "chunk.overlap, retrieval.top_k"
        : presetId === "custom_topk"
          ? "retrieval.mode, retrieval.top_k"
          : Object.keys(selectedPreset?.fixed ?? {}).join(", ") || t("common.none");

  const sweptAxes =
    labMode === "prep"
      ? "prep.pipeline"
      : labMode === "chunk"
        ? "chunk.size"
        : presetId === "custom_topk"
          ? t("common.none")
          : Object.keys(selectedPreset?.swept ?? {}).join(", ") || t("common.none");

  const start = useMutation({
    mutationFn: () => {
      const selectedTestSetId = testSetId || testSets[0]?.id;
      if (!selectedTestSetId) {
        throw new Error(t("newRunPage.needTestSet"));
      }
      if (labMode === "prep") {
        return createExperiment({
          project_id: projectId,
          evaluates: "prep",
          raw_bundle_id: rawBundleId || rawBundles[0]?.id,
          test_set_id: selectedTestSetId,
          fixed: {
            "chunk.size": 512,
            "chunk.overlap": 64,
            "retrieval.top_k": 5,
          },
          swept: {
            "prep.pipeline": ["plaintext", "pdf_clean"],
          },
        });
      }
      if (labMode === "chunk") {
        if (!chunkLabPreviewFresh) {
          throw new Error(t("newRunPage.chunkPreviewRequired"));
        }
        return createExperiment({
          project_id: projectId,
          evaluates: "chunk",
          clean_corpus_id: cleanCorpusId || cleanCorpora[0]?.id,
          test_set_id: selectedTestSetId,
          fixed: {
            "chunk.overlap": 64,
            "retrieval.top_k": 5,
          },
          swept: {
            "chunk.size": [256, 512, 1024],
          },
        });
      }

      let fixed: Record<string, unknown> = {};
      let swept: Record<string, unknown[]> = {};

      if (presetId === "custom_topk") {
        const k = Number(customTopK);
        if (!Number.isFinite(k) || k <= 0) {
          throw new Error(t("newRunPage.topKPositive"));
        }
        fixed = { "retrieval.mode": "dense", "retrieval.top_k": k };
      } else if (selectedPreset) {
        fixed = { ...selectedPreset.fixed };
        swept = { ...selectedPreset.swept };
      }

      ({ fixed, swept } = applyQuantizationChoice(fixed, swept, quantization));

      if (modelForRun) {
        fixed = { ...fixed, "embedding.model": modelForRun };
      }
      if (enableRerank) {
        fixed = {
          ...fixed,
          "rerank.enabled": true,
          "rerank.model": rerankModelId.trim(),
        };
      }

      return createExperiment({
        project_id: projectId,
        evaluates: "retrieval",
        chunk_set_id: chunkSetId || chunkSets[0]?.id,
        test_set_id: selectedTestSetId,
        fixed,
        swept,
      });
    },
    onSuccess: (run) => {
      void qc.invalidateQueries({ queryKey: ["experiments", projectId] });
      router.push(`/projects/${projectId}/runs/${run.id}`);
    },
  });

  return {
    project,
    labMode,
    setLabMode,
    ready,
    hasStartArtifact,
    emptyChunkSets,
    chunkSets,
    testSets,
    rawBundles,
    cleanCorpora,
    chunkSetId,
    setChunkSetId,
    rawBundleId,
    setRawBundleId,
    cleanCorpusId,
    setCleanCorpusId,
    testSetId,
    setTestSetId,
    presetId,
    setPresetId,
    customTopK,
    setCustomTopK,
    enableRerank,
    setEnableRerank,
    embeddingModelOverride,
    setEmbeddingModelOverride,
    quantization,
    setQuantization,
    selectedChunkSet,
    selectedCleanCorpusId,
    chunkLabPreview,
    chunkLabPreviewFresh,
    embeddingConfig,
    currentEmbedding,
    embeddingModelId,
    modelForRun,
    embeddingDimensionForRun,
    rerankModelId,
    qdrantSummary,
    configCount,
    fixedAxes,
    sweptAxes,
    start,
  };
}

export type NewRunFormState = ReturnType<typeof useNewRunForm>;

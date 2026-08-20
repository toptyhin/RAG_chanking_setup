import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchModelStorageSizes,
  listCachedEmbeddings,
  listCachedReranks,
  listLoadedEmbeddings,
  listLoadedReranks,
  loadEmbeddingModel,
  loadRerankModel,
  searchEmbeddingModels,
  searchRerankModels,
  setCurrentEmbedding,
  setCurrentRerank,
  subscribeModelJobProgress,
} from "@/lib/api";
import { useI18n } from "@/lib/locale";
import type { HubModel, ModelLoadJob } from "@/lib/types";
import type { ModelPickerKind } from "@/components/model-picker-types";

type UseModelPickerArgs = {
  kind: ModelPickerKind;
  value: string;
  onChange: (modelId: string) => void;
};

export function useModelPicker({ kind, value, onChange }: UseModelPickerArgs) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [job, setJob] = useState<ModelLoadJob | null>(null);
  const [loading, setLoading] = useState(false);

  const syncCurrent = useCallback(
    async (modelId: string) => {
      const mid = modelId.trim();
      if (!mid) return;
      try {
        if (kind === "embedding") {
          await setCurrentEmbedding(mid);
          await qc.invalidateQueries({ queryKey: ["models", "embedding", "current"] });
          await qc.invalidateQueries({ queryKey: ["models", "embedding", "loaded"] });
        } else {
          await setCurrentRerank(mid);
          await qc.invalidateQueries({ queryKey: ["models", "rerank", "current"] });
          await qc.invalidateQueries({ queryKey: ["models", "rerank", "loaded"] });
        }
      } catch {
        /* model may not be loaded yet; load path retries after ready */
      }
    },
    [kind, qc],
  );

  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(query.trim()), 350);
    return () => window.clearTimeout(id);
  }, [query]);

  const loaded = useQuery({
    queryKey: ["models", kind, "loaded"],
    queryFn: () =>
      kind === "embedding" ? listLoadedEmbeddings() : listLoadedReranks(),
  });

  const cached = useQuery({
    queryKey: ["models", kind, "cached", debounced],
    queryFn: () =>
      kind === "embedding"
        ? listCachedEmbeddings(debounced)
        : listCachedReranks(debounced),
  });

  const search = useQuery({
    queryKey: ["models", kind, "search", debounced],
    queryFn: () =>
      kind === "embedding"
        ? searchEmbeddingModels(debounced)
        : searchRerankModels(debounced),
    enabled: debounced.length >= 2 || debounced.length === 0,
  });

  const loadedIds = useMemo(() => {
    const rows = loaded.data ?? [];
    return new Set(rows.map((r) => r.model_id));
  }, [loaded.data]);

  const loadedDimById = useMemo(() => {
    const map = new Map<string, number>();
    if (kind !== "embedding") return map;
    for (const row of loaded.data ?? []) {
      if ("dimension" in row && typeof row.dimension === "number") {
        map.set(row.model_id, row.dimension);
      }
    }
    return map;
  }, [kind, loaded.data]);

  const cachedById = useMemo(() => {
    const map = new Map<string, { size_bytes: number | null; in_memory: boolean }>();
    for (const row of cached.data ?? []) {
      map.set(row.model_id, {
        size_bytes: row.size_bytes,
        in_memory: row.in_memory,
      });
    }
    return map;
  }, [cached.data]);

  const searchItems = search.data?.items;
  const items: HubModel[] = searchItems ?? [];
  const itemIdsKey = useMemo(
    () => (searchItems ?? []).map((m) => m.id).join("\n"),
    [searchItems],
  );

  const [sizeById, setSizeById] = useState<Map<string, number | null>>(
    () => new Map(),
  );
  const [sizesLoading, setSizesLoading] = useState(false);

  useEffect(() => {
    if (!search.isSuccess || !itemIdsKey) {
      setSizeById(new Map());
      setSizesLoading(false);
      return;
    }
    const ids = itemIdsKey.split("\n").filter(Boolean);
    let cancelled = false;
    setSizesLoading(true);
    void fetchModelStorageSizes(ids)
      .then((res) => {
        if (cancelled) return;
        const map = new Map<string, number | null>();
        for (const row of res.items) {
          const local = cachedById.get(row.model_id)?.size_bytes;
          map.set(row.model_id, local ?? row.size_bytes);
        }
        setSizeById(map);
      })
      .catch(() => {
        if (!cancelled) {
          const map = new Map<string, number | null>();
          for (const id of ids) {
            const local = cachedById.get(id)?.size_bytes;
            if (local != null) map.set(id, local);
          }
          setSizeById(map);
        }
      })
      .finally(() => {
        if (!cancelled) setSizesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [search.isSuccess, itemIdsKey, cachedById]);

  useEffect(() => {
    if (!job?.job_id) return;
    if (job.stage === "ready" || job.stage === "failed") return;
    const jobId = job.job_id;
    return subscribeModelJobProgress(jobId, (next, event) => {
      setJob(next);
      if (event === "done" || next.stage === "ready") {
        setLoading(false);
        onChange(next.model_id);
        void syncCurrent(next.model_id);
        void loaded.refetch();
        void cached.refetch();
      }
      if (event === "error" || next.stage === "failed") {
        setLoading(false);
        setLoadError(next.error || next.message || t("modelPicker.loadFailed"));
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- one SSE per job_id
  }, [job?.job_id]);

  const selectModel = useCallback(
    (modelId: string) => {
      onChange(modelId);
      if (kind === "embedding" ? loadedIds.has(modelId) : true) {
        void syncCurrent(modelId);
      }
    },
    [kind, loadedIds, onChange, syncCurrent],
  );

  async function onLoad(modelId: string) {
    setLoadError(null);
    setLoading(true);
    try {
      const started =
        kind === "embedding"
          ? await loadEmbeddingModel(modelId)
          : await loadRerankModel(modelId);
      setJob(started);
      onChange(modelId);
      if (started.stage === "ready") {
        setLoading(false);
        await syncCurrent(modelId);
        void loaded.refetch();
        void cached.refetch();
      }
    } catch (err) {
      setLoading(false);
      setLoadError((err as Error).message);
    }
  }

  const progress =
    job && job.model_id === value && job.stage !== "ready"
      ? job
      : loading && job
        ? job
        : null;

  return {
    t,
    kind,
    value,
    onChange: selectModel,
    query,
    setQuery,
    loadError,
    loading,
    progress,
    loaded,
    cached,
    search,
    items,
    loadedIds,
    loadedDimById,
    cachedById,
    sizeById,
    sizesLoading,
    onLoad,
  };
}

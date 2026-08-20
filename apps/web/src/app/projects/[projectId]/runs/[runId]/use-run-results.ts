"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { getExperiment, getProject, subscribeExperimentProgress } from "@/lib/api";
import {
  bestRowByRecall,
  isHiddenMetric,
  isPrimaryMetric,
  recallFromMetrics,
} from "@/lib/metrics";
import type { ExperimentProgressEvent, MetricsRow } from "@/lib/types";
import { metricSize, rowForPoint } from "./run-results-utils";

export function useRunResults(projectId: string, runId: string) {
  const queryClient = useQueryClient();
  const [liveProgress, setLiveProgress] = useState<ExperimentProgressEvent | null>(null);

  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });

  const experiment = useQuery({
    queryKey: ["experiment", runId],
    queryFn: () => getExperiment(runId),
  });

  useEffect(
    () =>
      subscribeExperimentProgress(runId, (event, eventName) => {
        setLiveProgress(event);
        if (
          eventName === "done" ||
          event.status === "completed" ||
          event.status === "failed"
        ) {
          void queryClient.invalidateQueries({
            queryKey: ["experiment", runId],
          });
        }
      }),
    [runId, queryClient],
  );

  const rows = useMemo(
    () => experiment.data?.metrics_rows ?? [],
    [experiment.data?.metrics_rows],
  );
  const pareto = useMemo(
    () => experiment.data?.pareto ?? [],
    [experiment.data?.pareto],
  );
  const best = useMemo(() => bestRowByRecall(rows), [rows]);
  const bestRecall = best ? recallFromMetrics(best.metrics) : null;

  const primaryKeys = Array.from(
    new Set(rows.flatMap((r) => Object.keys(r.metrics ?? {}))),
  )
    .filter(isPrimaryMetric)
    .sort();

  const secondaryKeys = Array.from(
    new Set(rows.flatMap((r) => Object.keys(r.metrics ?? {}))),
  )
    .filter((k) => !isPrimaryMetric(k) && !isHiddenMetric(k))
    .sort();

  const progress = liveProgress ?? experiment.data?.progress;
  const chartData = useMemo(
    () =>
      pareto.map((p) => ({
        name: `#${p.point_index}`,
        recall: p.recall,
        latency: p.latency_p95_ms,
        size: p.index_size_mb,
      })),
    [pareto],
  );

  const recommendations = useMemo(() => {
    if (rows.length === 0) return { quality: null, balanced: null, memory: null };
    const quality = best;
    const memory =
      [...rows]
        .filter((row) => metricSize(row) != null)
        .sort((a, b) => (metricSize(a) ?? Infinity) - (metricSize(b) ?? Infinity))[0] ?? null;
    const latencies = pareto.map((p) => p.latency_p95_ms);
    const sizes = pareto.map((p) => p.index_size_mb);
    const maxLatency = Math.max(...latencies, 1);
    const maxSize = Math.max(...sizes, 1);
    const balancedPoint = [...pareto].sort(
      (a, b) =>
        b.recall - b.latency_p95_ms / maxLatency * 0.15 - b.index_size_mb / maxSize * 0.1 -
        (a.recall - a.latency_p95_ms / maxLatency * 0.15 - a.index_size_mb / maxSize * 0.1),
    )[0];
    return {
      quality,
      balanced: rowForPoint(rows, balancedPoint) ?? quality,
      memory:
        memory ??
        rowForPoint(rows, [...pareto].sort((a, b) => a.index_size_mb - b.index_size_mb)[0]) ??
        quality,
    };
  }, [rows, pareto, best]);

  return {
    project,
    experiment,
    rows,
    best,
    bestRecall,
    primaryKeys,
    secondaryKeys,
    progress,
    pareto,
    chartData,
    recommendations,
  };
}

export type RunRecommendations = {
  quality: MetricsRow | null;
  balanced: MetricsRow | null;
  memory: MetricsRow | null;
};

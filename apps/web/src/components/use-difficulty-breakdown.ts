import { useMemo, useState } from "react";
import { useI18n } from "@/lib/locale";
import { bestRowByRecall } from "@/lib/metrics";
import {
  buildDifficultyCurve,
  buildDifficultyGroupedByConfig,
  buildHeatmapMatrix,
  flattenQueryTypeBreakdown,
  listBreakdownMetrics,
  listHeatmapMetrics,
  overallMetricValue,
} from "@/lib/query-type";
import type { MetricsRow } from "@/lib/types";

export function useDifficultyBreakdown(rows: MetricsRow[]) {
  const { t } = useI18n();

  const withBreakdown = useMemo(
    () =>
      rows.filter((r) => flattenQueryTypeBreakdown(r.metrics).length > 0),
    [rows],
  );

  const allFlat = useMemo(
    () => withBreakdown.flatMap((r) => flattenQueryTypeBreakdown(r.metrics)),
    [withBreakdown],
  );

  const chartMetrics = useMemo(
    () => listBreakdownMetrics(allFlat),
    [allFlat],
  );
  const heatmapMetricOptions = useMemo(
    () => listHeatmapMetrics(allFlat),
    [allFlat],
  );

  const defaultMetric =
    chartMetrics.find((m) => m.startsWith("recall@")) ?? chartMetrics[0] ?? "";

  const best = bestRowByRecall(withBreakdown);
  const defaultPoint =
    best?.point_index ?? withBreakdown[0]?.point_index ?? 0;

  const [metric, setMetric] = useState(defaultMetric);
  const [matrixPoint, setMatrixPoint] = useState(defaultPoint);

  const activeMetric =
    metric && chartMetrics.includes(metric) ? metric : defaultMetric;
  const activePoint = withBreakdown.some((r) => r.point_index === matrixPoint)
    ? matrixPoint
    : defaultPoint;

  const matrixRow =
    withBreakdown.find((r) => r.point_index === activePoint) ??
    withBreakdown[0];

  const configInputs = useMemo(
    () =>
      withBreakdown.map((r) => ({
        pointIndex: r.point_index,
        metrics: r.metrics,
      })),
    [withBreakdown],
  );

  const curve = useMemo(
    () => buildDifficultyCurve(configInputs, activeMetric),
    [configInputs, activeMetric],
  );

  const grouped = useMemo(
    () => buildDifficultyGroupedByConfig(configInputs, activeMetric),
    [configInputs, activeMetric],
  );

  const heatmap = useMemo(
    () =>
      buildHeatmapMatrix(
        matrixRow?.metrics,
        heatmapMetricOptions.length > 0 ? heatmapMetricOptions : undefined,
      ),
    [matrixRow, heatmapMetricOptions],
  );

  const overallForChart = overallMetricValue(matrixRow?.metrics, activeMetric);
  const singleSeries = withBreakdown.length === 1;
  const chartHasData = singleSeries
    ? curve.data.some((d) =>
        curve.series.some((s) => typeof d[s.key] === "number"),
      )
    : grouped.data.some((d) =>
        grouped.types.some((type) => typeof d[type] === "number"),
      );

  return {
    t,
    withBreakdown,
    chartMetrics,
    activeMetric,
    setMetric,
    activePoint,
    setMatrixPoint,
    best,
    matrixRow,
    curve,
    grouped,
    heatmap,
    overallForChart,
    singleSeries,
    chartHasData,
  };
}

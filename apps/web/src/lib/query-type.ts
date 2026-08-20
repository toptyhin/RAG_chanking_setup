/** Normalize difficulty / query_type labels for metrics breakdown. */

export const ORDERED_DIFFICULTY_LEVELS = ["l1", "l2", "l3", "l4"] as const;

export type DifficultyLevelId = (typeof ORDERED_DIFFICULTY_LEVELS)[number];

export type BreakdownRow = { type: string; metric: string; value: number };

const METRIC_PREF = [
  "recall@5",
  "recall@10",
  "recall@1",
  "ndcg@5",
  "ndcg@10",
  "ndcg@1",
  "mrr",
] as const;

export function normalizeQueryType(
  value: string | null | undefined,
): string | undefined {
  if (value == null) return undefined;
  const s = value
    .trim()
    .toLowerCase()
    .replace(/_/g, "-")
    .split(/\s+/)
    .filter(Boolean)
    .join("-");
  return s || undefined;
}

export function resolveQueryType(opts: {
  queryType?: string | null;
  level?: string | null;
  meta?: Record<string, unknown> | null;
}): string | undefined {
  if (opts.queryType?.trim()) return normalizeQueryType(opts.queryType);
  if (opts.level?.trim()) return normalizeQueryType(opts.level);
  const meta = opts.meta;
  if (meta) {
    for (const key of ["query_type", "level", "difficulty"] as const) {
      const raw = meta[key];
      if (typeof raw === "string" && raw.trim()) {
        return normalizeQueryType(raw);
      }
    }
  }
  return undefined;
}

/** Flatten ``metrics.by_query_type`` into sorted rows for display. */
export function flattenQueryTypeBreakdown(
  metrics: Record<string, unknown> | undefined,
): BreakdownRow[] {
  const raw = metrics?.by_query_type;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return [];
  const rows: BreakdownRow[] = [];
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof value !== "number") continue;
    const dot = key.lastIndexOf(".");
    if (dot <= 0) {
      rows.push({ type: key, metric: key, value });
      continue;
    }
    rows.push({
      type: key.slice(0, dot),
      metric: key.slice(dot + 1),
      value,
    });
  }
  rows.sort((a, b) =>
    a.type === b.type
      ? a.metric.localeCompare(b.metric)
      : a.type.localeCompare(b.type),
  );
  return rows;
}

/** L1–L4 first (ordinal), then other types alphabetically. */
export function orderQueryTypes(types: Iterable<string>): string[] {
  const set = new Set(types);
  const ordered: string[] = [];
  for (const level of ORDERED_DIFFICULTY_LEVELS) {
    if (set.has(level)) {
      ordered.push(level);
      set.delete(level);
    }
  }
  return [...ordered, ...Array.from(set).sort((a, b) => a.localeCompare(b))];
}

/** Unique metric names, preferred keys first. */
export function listBreakdownMetrics(rows: BreakdownRow[]): string[] {
  const present = new Set(rows.map((r) => r.metric));
  const preferredSet = new Set<string>(METRIC_PREF);
  const preferred = METRIC_PREF.filter((m) => present.has(m));
  const rest = Array.from(present)
    .filter((m) => !preferredSet.has(m))
    .sort((a, b) => a.localeCompare(b));
  return [...preferred, ...rest];
}

/** Metrics useful as heatmap columns (recall / ndcg / mrr). */
export function listHeatmapMetrics(rows: BreakdownRow[]): string[] {
  return listBreakdownMetrics(rows).filter(
    (m) =>
      m.startsWith("recall@") || m.startsWith("ndcg@") || m === "mrr",
  );
}

export function breakdownValue(
  rows: BreakdownRow[],
  type: string,
  metric: string,
): number | null {
  const hit = rows.find((r) => r.type === type && r.metric === metric);
  return hit ? hit.value : null;
}

/** Overall (non-breakdown) metric from the row, e.g. ``recall@5``. */
export function overallMetricValue(
  metrics: Record<string, unknown> | undefined,
  metric: string,
): number | null {
  if (!metrics) return null;
  const v = metrics[metric];
  return typeof v === "number" ? v : null;
}

export function deltaVsOverall(
  value: number | null,
  overall: number | null,
): number | null {
  if (value == null || overall == null) return null;
  return value - overall;
}

/** Display label for axis / legend: ``l1`` → ``L1``. */
export function formatDifficultyLabel(type: string): string {
  const n = type.trim().toLowerCase();
  if (
    n === "l1" ||
    n === "l2" ||
    n === "l3" ||
    n === "l4" ||
    /^l[1-4]\b/.test(n)
  ) {
    return n.slice(0, 2).toUpperCase();
  }
  return type;
}

export type DifficultyCurvePoint = {
  type: string;
  label: string;
} & Record<string, string | number | null>;

export type DifficultyCurveSeries = {
  key: string;
  pointIndex: number;
  label: string;
};

/** Chart rows: one point per query type, series columns per config. */
export function buildDifficultyCurve(
  configs: {
    pointIndex: number;
    metrics: Record<string, unknown>;
  }[],
  metric: string,
): { data: DifficultyCurvePoint[]; series: DifficultyCurveSeries[] } {
  const typeSet = new Set<string>();
  const byConfig = configs.map((c) => {
    const flat = flattenQueryTypeBreakdown(c.metrics);
    for (const row of flat) typeSet.add(row.type);
    return { config: c, flat };
  });
  const types = orderQueryTypes(typeSet);
  const series: DifficultyCurveSeries[] = configs.map((c) => ({
    key: `p${c.pointIndex}`,
    pointIndex: c.pointIndex,
    label: `#${c.pointIndex}`,
  }));
  const data: DifficultyCurvePoint[] = types.map((type) => {
    const point: DifficultyCurvePoint = {
      type,
      label: formatDifficultyLabel(type),
    };
    byConfig.forEach(({ config, flat }, i) => {
      const key = series[i]?.key ?? `p${config.pointIndex}`;
      point[key] = breakdownValue(flat, type, metric);
    });
    return point;
  });
  return { data, series };
}

export type DifficultyGroupedPoint = {
  configLabel: string;
  pointIndex: number;
} & Record<string, string | number | null>;

/**
 * Grouped bars: one row per config, columns = difficulty types (legend L1–L4).
 */
export function buildDifficultyGroupedByConfig(
  configs: {
    pointIndex: number;
    metrics: Record<string, unknown>;
  }[],
  metric: string,
): { data: DifficultyGroupedPoint[]; types: string[] } {
  const typeSet = new Set<string>();
  const flats = configs.map((c) => {
    const flat = flattenQueryTypeBreakdown(c.metrics);
    for (const row of flat) typeSet.add(row.type);
    return flat;
  });
  const types = orderQueryTypes(typeSet);
  const data: DifficultyGroupedPoint[] = configs.map((c, i) => {
    const point: DifficultyGroupedPoint = {
      configLabel: `#${c.pointIndex}`,
      pointIndex: c.pointIndex,
    };
    for (const type of types) {
      point[type] = breakdownValue(flats[i]!, type, metric);
    }
    return point;
  });
  return { data, types };
}

export type HeatmapCell = {
  type: string;
  metric: string;
  value: number | null;
  delta: number | null;
};

export function buildHeatmapMatrix(
  metrics: Record<string, unknown> | undefined,
  metricColumns?: string[],
): { types: string[]; metrics: string[]; cells: HeatmapCell[] } {
  const flat = flattenQueryTypeBreakdown(metrics);
  const types = orderQueryTypes(new Set(flat.map((r) => r.type)));
  const cols =
    metricColumns && metricColumns.length > 0
      ? metricColumns
      : listHeatmapMetrics(flat);
  const cells: HeatmapCell[] = [];
  for (const type of types) {
    for (const metric of cols) {
      const value = breakdownValue(flat, type, metric);
      const overall = overallMetricValue(metrics, metric);
      cells.push({
        type,
        metric,
        value,
        delta: deltaVsOverall(value, overall),
      });
    }
  }
  return { types, metrics: cols, cells };
}

/** Background tint for a 0–1 score (heatmap). */
export function heatmapCellStyle(value: number | null): {
  backgroundColor: string;
  color?: string;
} {
  if (value == null || Number.isNaN(value)) {
    return { backgroundColor: "transparent" };
  }
  const t = Math.max(0, Math.min(1, value));
  // Soft emerald scale aligned with --accent (~#0f6e56)
  const alpha = 0.08 + t * 0.42;
  return {
    backgroundColor: `color-mix(in srgb, var(--accent) ${Math.round(alpha * 100)}%, transparent)`,
  };
}

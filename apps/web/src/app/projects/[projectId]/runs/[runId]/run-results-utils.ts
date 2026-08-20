import type { MetricsRow, ParetoPoint } from "@/lib/types";

export function metricSize(row: MetricsRow): number | null {
  for (const key of ["index_ram_mb", "index_disk_mb", "index_size_mb"]) {
    const value = row.metrics[key];
    if (typeof value === "number") return value;
  }
  return null;
}

export function rowForPoint(rows: MetricsRow[], point: ParetoPoint | undefined) {
  return point ? rows.find((row) => row.point_index === point.point_index) ?? null : null;
}

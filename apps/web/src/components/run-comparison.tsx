"use client";

import { useEffect, useMemo, useState } from "react";
import { useQueries } from "@tanstack/react-query";
import Link from "next/link";
import { getExperiment } from "@/lib/api";
import { bestRowByRecall, formatMetricValue, recallFromMetrics } from "@/lib/metrics";
import { useI18n } from "@/lib/locale";
import type { Experiment, MetricsRow } from "@/lib/types";
import { Callout, Select } from "@/components/ui";

function metric(row: MetricsRow | null, keys: string[]): number | null {
  if (!row) return null;
  for (const key of keys) {
    const value = row.metrics[key];
    if (typeof value === "number") return value;
  }
  return null;
}

function bestRow(run: Experiment | undefined): MetricsRow | null {
  return run ? bestRowByRecall(run.metrics_rows) : null;
}

function valueLabel(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "boolean") return value ? "on" : "off";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function RunComparison({
  projectId,
  runs,
}: {
  projectId: string;
  runs: Experiment[];
}) {
  const { t } = useI18n();
  const completed = useMemo(
    () => runs.filter((run) => run.status === "completed"),
    [runs],
  );
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [baselineId, setBaselineId] = useState("");

  useEffect(() => {
    if (selectedIds.length === 0 && completed.length >= 2) {
      const initial = completed.slice(0, 2).map((run) => run.id);
      setSelectedIds(initial);
      setBaselineId(initial[0]);
    }
  }, [completed, selectedIds.length]);

  const queries = useQueries({
    queries: selectedIds.map((id) => ({
      queryKey: ["experiment", id],
      queryFn: () => getExperiment(id),
    })),
  });
  const selectedRuns = queries
    .map((query) => query.data)
    .filter((run): run is Experiment => Boolean(run));
  const selectedIdSet = useMemo(() => new Set(selectedIds), [selectedIds]);
  const baselineRun =
    selectedRuns.find((run) => run.id === baselineId) ?? selectedRuns[0];
  const baselineRow = bestRow(baselineRun);
  const baselineRecall = baselineRow ? recallFromMetrics(baselineRow.metrics) : null;

  function toggle(runId: string) {
    const next = selectedIdSet.has(runId)
      ? selectedIds.filter((id) => id !== runId)
      : [...selectedIds, runId];
    setSelectedIds(next);
    if (!next.includes(baselineId)) {
      setBaselineId(next[0] ?? "");
    }
  }

  if (completed.length < 2) {
    return (
      <p className="text-sm text-[var(--muted)]">
        {t("compare.needTwoRuns")}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-[var(--muted)]">{t("compare.intro")}</p>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {completed.map((run) => (
          <label
            key={run.id}
            className="flex items-start gap-2 rounded-md border border-[var(--border)] px-3 py-2 text-sm"
          >
            <input
              type="checkbox"
              className="mt-1"
              checked={selectedIdSet.has(run.id)}
              onChange={() => toggle(run.id)}
            />
            <span>
              <span className="block font-medium">
                {run.evaluates} · {run.id.slice(0, 12)}
              </span>
              <span className="text-xs text-[var(--muted)]">
                {Object.keys(run.swept).join(", ") || t("compare.singleConfig")}
              </span>
            </span>
          </label>
        ))}
      </div>

      {selectedIds.length < 2 ? (
        <Callout tone="warning">{t("compare.selectTwo")}</Callout>
      ) : (
        <>
          <div className="max-w-sm">
            <label
              htmlFor="compare-baseline"
              className="text-sm font-medium"
            >
              {t("compare.baseline")}
            </label>
            <Select
              id="compare-baseline"
              className="mt-1"
              value={baselineRun?.id ?? ""}
              onChange={(event) => setBaselineId(event.target.value)}
            >
              {selectedRuns.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.evaluates} · {run.id.slice(0, 12)}
                </option>
              ))}
            </Select>
          </div>

          {queries.some((query) => query.isLoading) ? (
            <p className="text-sm text-[var(--muted)]">{t("common.loading")}</p>
          ) : null}

          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  <th className="py-2 pr-4 font-medium">{t("compare.metric")}</th>
                  {selectedRuns.map((run) => (
                    <th key={run.id} className="py-2 pr-4 font-medium">
                      <Link
                        href={`/projects/${projectId}/runs/${run.id}`}
                        className="text-[var(--accent)] underline"
                      >
                        {run.evaluates} · {run.id.slice(0, 8)}
                      </Link>
                      {run.id === baselineRun?.id ? (
                        <span className="ml-2 text-xs text-[var(--muted)]">
                          {t("compare.baselineMark")}
                        </span>
                      ) : null}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  ["Recall", (row: MetricsRow | null) => row ? recallFromMetrics(row.metrics) : null],
                  ["MRR", (row: MetricsRow | null) => metric(row, ["mrr"])],
                  ["nDCG", (row: MetricsRow | null) => metric(row, ["ndcg@10", "ndcg@5"])],
                  [t("compare.latency"), (row: MetricsRow | null) => row?.latency_p95_ms ?? null],
                  [t("compare.indexSize"), (row: MetricsRow | null) => metric(row, ["index_ram_mb", "index_disk_mb", "index_size_mb"])],
                ].map(([label, getter]) => (
                  <tr key={String(label)} className="border-b border-[var(--border)]">
                    <td className="py-2 pr-4 font-medium">{String(label)}</td>
                    {selectedRuns.map((run) => {
                      const value = (getter as (row: MetricsRow | null) => number | null)(bestRow(run));
                      return (
                        <td key={run.id} className="py-2 pr-4">
                          {value == null ? "—" : formatMetricValue(value)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
                <tr className="border-b border-[var(--border)]">
                  <td className="py-2 pr-4 font-medium">{t("compare.recallDelta")}</td>
                  {selectedRuns.map((run) => {
                    const row = bestRow(run);
                    const recall = row ? recallFromMetrics(row.metrics) : null;
                    const delta =
                      recall != null && baselineRecall != null
                        ? recall - baselineRecall
                        : null;
                    return (
                      <td key={run.id} className="py-2 pr-4">
                        {delta == null
                          ? "—"
                          : `${delta >= 0 ? "+" : ""}${delta.toFixed(3)}`}
                      </td>
                    );
                  })}
                </tr>
              </tbody>
            </table>
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            {selectedRuns.flatMap((run) => {
              if (run.id === baselineRun?.id) return [];
              const row = bestRow(run);
              const baselineConfig = baselineRow?.config ?? {};
              const config = row?.config ?? {};
              const keys = Array.from(
                new Set([...Object.keys(baselineConfig), ...Object.keys(config)]),
              ).filter(
                (key) => valueLabel(config[key]) !== valueLabel(baselineConfig[key]),
              );
              return [
                <article
                  key={run.id}
                  className="rounded-lg border border-[var(--border)] p-4"
                >
                  <h3 className="text-sm font-semibold">
                    {t("compare.configDiff")} · {run.id.slice(0, 8)}
                  </h3>
                  {keys.length === 0 ? (
                    <p className="mt-2 text-sm text-[var(--muted)]">
                      {t("compare.noConfigDiff")}
                    </p>
                  ) : (
                    <ul className="mt-2 space-y-1 text-sm">
                      {keys.map((key) => (
                        <li key={key}>
                          <code className="text-xs">{key}</code>:{" "}
                          <span className="text-[var(--muted)]">
                            {valueLabel(baselineConfig[key])}
                          </span>{" "}
                          → {valueLabel(config[key])}
                        </li>
                      ))}
                    </ul>
                  )}
                </article>,
              ];
            })}
          </div>
        </>
      )}
    </div>
  );
}

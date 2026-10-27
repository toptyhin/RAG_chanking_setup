"use client";

import { Callout } from "@/components/ui";
import { isFailedRow, rowError } from "@/lib/metrics";
import { useI18n } from "@/lib/locale";
import type { Experiment, MetricsRow } from "@/lib/types";

type RunResultsFailureNoticeProps = {
  experiment: Experiment | undefined;
  rows: MetricsRow[];
  failedPoints: number;
};

/**
 * Surfaces failed runs / failed grid points. The backend records per-point
 * failures as `metrics.status = "failed"`; without this block the only trace
 * used to leak into the operational-metrics table.
 */
export function RunResultsFailureNotice({
  experiment,
  rows,
  failedPoints,
}: RunResultsFailureNoticeProps) {
  const { t } = useI18n();

  const runError = experiment?.error ?? null;
  const failedRows = rows.filter(isFailedRow);
  if (!runError && failedPoints === 0 && failedRows.length === 0) return null;

  const total = rows.length || experiment?.progress?.total || failedPoints;
  const allFailed = total > 0 && failedPoints >= total;
  const title = runError
    ? t("runPage.failureTitle")
    : allFailed
      ? t("runPage.allFailedTitle")
      : t("runPage.partialFailureTitle");

  return (
    <Callout tone="warning" className="mb-6">
      <strong>{title}</strong>{" "}
      {runError ?? t("runPage.failurePoints", { failed: failedPoints, total })}
      {!runError && failedRows.length > 0 ? (
        <ul className="mt-2 list-none space-y-0.5 text-xs">
          {failedRows.map((row) => (
            <li key={row.id}>
              {t("runPage.failurePoint", {
                index: row.point_index,
                error: rowError(row) ?? t("common.emDash"),
              })}
            </li>
          ))}
        </ul>
      ) : null}
    </Callout>
  );
}

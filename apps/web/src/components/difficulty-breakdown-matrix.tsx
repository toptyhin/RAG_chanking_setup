"use client";

import { DifficultyBadge } from "@/components/difficulty-badge";
import { formatDifficultyDelta } from "@/components/difficulty-breakdown-utils";
import { heatmapCellStyle } from "@/lib/query-type";
import type { useDifficultyBreakdown } from "@/components/use-difficulty-breakdown";

type BreakdownState = ReturnType<typeof useDifficultyBreakdown>;

type Props = Pick<BreakdownState, "t" | "matrixRow" | "heatmap">;

export function DifficultyBreakdownMatrix({ t, matrixRow, heatmap }: Props) {
  if (!matrixRow) return null;

  return (
    <div>
      <p className="mb-2 text-sm font-medium text-[var(--fg)]">
        {t("runPage.byTypeMatrixTitle")}
        <span className="ml-2 font-normal text-[var(--muted)]">
          #{matrixRow.point_index}
        </span>
      </p>
      <p className="mb-3 text-xs text-[var(--muted)]">
        {t("runPage.byTypeMatrixHint")}
      </p>
      {heatmap.types.length === 0 || heatmap.metrics.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">
          {t("runPage.byTypeNoMatrix")}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                <th className="py-2 pr-3 font-medium">
                  {t("runPage.byTypeCol")}
                </th>
                {heatmap.metrics.map((m) => (
                  <th key={m} className="py-2 pr-3 font-medium">
                    {m}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {heatmap.types.map((type) => (
                <tr key={type} className="border-b border-[var(--border)]">
                  <td className="py-2 pr-3">
                    <DifficultyBadge
                      level={type}
                      queryType={type}
                      showShort
                    />
                  </td>
                  {heatmap.metrics.map((m) => {
                    const cell = heatmap.cells.find(
                      (c) => c.type === type && c.metric === m,
                    );
                    const value = cell?.value ?? null;
                    const delta = cell?.delta ?? null;
                    return (
                      <td
                        key={m}
                        className="py-2 pr-3"
                        style={heatmapCellStyle(value)}
                      >
                        <div className="font-medium tabular-nums">
                          {value != null ? value.toFixed(3) : "—"}
                        </div>
                        {delta != null ? (
                          <div
                            className={`text-[11px] tabular-nums ${
                              delta < -0.02
                                ? "text-[var(--danger)]"
                                : delta > 0.02
                                  ? "text-[var(--accent)]"
                                  : "text-[var(--muted)]"
                            }`}
                            title={t("runPage.byTypeDeltaHint")}
                          >
                            {formatDifficultyDelta(delta)}
                          </div>
                        ) : null}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-2 font-mono text-[11px] text-[var(--muted)]">
        {JSON.stringify(matrixRow.config)}
      </p>
    </div>
  );
}

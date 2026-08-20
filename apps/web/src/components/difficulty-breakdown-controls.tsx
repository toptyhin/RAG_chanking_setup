"use client";

import { Label, Select } from "@/components/ui";
import type { useDifficultyBreakdown } from "@/components/use-difficulty-breakdown";

type BreakdownState = ReturnType<typeof useDifficultyBreakdown>;

type Props = Pick<
  BreakdownState,
  | "t"
  | "withBreakdown"
  | "chartMetrics"
  | "activeMetric"
  | "setMetric"
  | "activePoint"
  | "setMatrixPoint"
  | "best"
>;

export function DifficultyBreakdownControls({
  t,
  withBreakdown,
  chartMetrics,
  activeMetric,
  setMetric,
  activePoint,
  setMatrixPoint,
  best,
}: Props) {
  return (
    <div className="flex flex-wrap items-end gap-4">
      <div className="min-w-[10rem]">
        <Label>{t("runPage.byTypeMetricSelect")}</Label>
        <Select
          value={activeMetric}
          onChange={(e) => setMetric(e.target.value)}
          aria-label={t("runPage.byTypeMetricSelect")}
        >
          {chartMetrics.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </Select>
      </div>
      {withBreakdown.length > 1 ? (
        <div className="min-w-[12rem]">
          <Label>{t("runPage.byTypeConfigSelect")}</Label>
          <Select
            value={String(activePoint)}
            onChange={(e) => setMatrixPoint(Number(e.target.value))}
            aria-label={t("runPage.byTypeConfigSelect")}
          >
            {withBreakdown.map((r) => (
              <option key={r.id} value={r.point_index}>
                #{r.point_index}
                {best && r.point_index === best.point_index
                  ? ` · ${t("runPage.byTypeBest")}`
                  : ""}
              </option>
            ))}
          </Select>
        </div>
      ) : null}
    </div>
  );
}

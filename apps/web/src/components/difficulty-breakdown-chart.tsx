"use client";

import { useEffect, useState } from "react";
import {
  difficultyTooltipStyle,
  fillForDifficultyType,
} from "@/components/difficulty-breakdown-utils";
import { formatDifficultyLabel } from "@/lib/query-type";
import type { useDifficultyBreakdown } from "@/components/use-difficulty-breakdown";

type BreakdownState = ReturnType<typeof useDifficultyBreakdown>;

type Props = Pick<
  BreakdownState,
  | "t"
  | "curve"
  | "grouped"
  | "activeMetric"
  | "overallForChart"
  | "singleSeries"
  | "chartHasData"
>;

export function DifficultyBreakdownChart({
  t,
  curve,
  grouped,
  activeMetric,
  overallForChart,
  singleSeries,
  chartHasData,
}: Props) {
  const [recharts, setRecharts] = useState<Awaited<
    typeof import("recharts")
  > | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const mod = await import("recharts");
        if (!cancelled) setRecharts(mod);
      } catch {
        // Keep placeholder if recharts fails to load.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <p className="mb-2 text-sm font-medium text-[var(--fg)]">
        {t("runPage.byTypeCurveTitle")}
      </p>
      <p className="mb-3 text-xs text-[var(--muted)]">
        {t("runPage.byTypeCurveHint")}
      </p>
      {!chartHasData ? (
        <p className="text-sm text-[var(--muted)]">
          {t("runPage.byTypeNoCurve")}
        </p>
      ) : !recharts ? (
        <div className="h-72 w-full" aria-hidden />
      ) : (
        <DifficultyBreakdownChartBody
          t={t}
          curve={curve}
          grouped={grouped}
          activeMetric={activeMetric}
          overallForChart={overallForChart}
          singleSeries={singleSeries}
          recharts={recharts}
        />
      )}
    </div>
  );
}

function DifficultyBreakdownChartBody({
  t,
  curve,
  grouped,
  activeMetric,
  overallForChart,
  singleSeries,
  recharts,
}: Omit<Props, "chartHasData"> & {
  recharts: Awaited<typeof import("recharts")>;
}) {
  const {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    Legend,
    ReferenceLine,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
  } = recharts;

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        {singleSeries ? (
          <BarChart
            data={curve.data}
            margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis
              dataKey="label"
              tick={{ fill: "var(--muted)", fontSize: 12 }}
            />
            <YAxis
              domain={[0, 1]}
              tick={{ fill: "var(--muted)", fontSize: 12 }}
            />
            <Tooltip
              contentStyle={difficultyTooltipStyle}
              formatter={(value) =>
                typeof value === "number" ? value.toFixed(3) : "—"
              }
              labelFormatter={(label) => String(label)}
            />
            <Legend
              content={() => (
                <ul className="mt-2 flex flex-wrap justify-center gap-3 text-xs text-[var(--muted)]">
                  {curve.data.map((d, i) => (
                    <li
                      key={d.type}
                      className="inline-flex items-center gap-1.5"
                    >
                      <span
                        className="inline-block size-2.5 rounded-sm"
                        style={{
                          backgroundColor: fillForDifficultyType(d.type, i),
                        }}
                        aria-hidden
                      />
                      {formatDifficultyLabel(d.type)}
                    </li>
                  ))}
                </ul>
              )}
            />
            {overallForChart != null ? (
              <ReferenceLine
                y={overallForChart}
                stroke="var(--muted)"
                strokeDasharray="4 4"
                label={{
                  value: t("runPage.byTypeOverall"),
                  fill: "var(--muted)",
                  fontSize: 11,
                  position: "insideTopRight",
                }}
              />
            ) : null}
            <Bar
              dataKey={curve.series[0]!.key}
              name={activeMetric}
              radius={[4, 4, 0, 0]}
              legendType="none"
            >
              {curve.data.map((d, i) => (
                <Cell key={d.type} fill={fillForDifficultyType(d.type, i)} />
              ))}
            </Bar>
          </BarChart>
        ) : (
          <BarChart
            data={grouped.data}
            margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis
              dataKey="configLabel"
              tick={{ fill: "var(--muted)", fontSize: 12 }}
            />
            <YAxis
              domain={[0, 1]}
              tick={{ fill: "var(--muted)", fontSize: 12 }}
            />
            <Tooltip
              contentStyle={difficultyTooltipStyle}
              formatter={(value, name) => [
                typeof value === "number" ? value.toFixed(3) : "—",
                formatDifficultyLabel(String(name)),
              ]}
            />
            <Legend
              formatter={(value) => formatDifficultyLabel(String(value))}
            />
            {overallForChart != null ? (
              <ReferenceLine
                y={overallForChart}
                stroke="var(--muted)"
                strokeDasharray="4 4"
                label={{
                  value: t("runPage.byTypeOverall"),
                  fill: "var(--muted)",
                  fontSize: 11,
                  position: "insideTopRight",
                }}
              />
            ) : null}
            {grouped.types.map((type, i) => (
              <Bar
                key={type}
                dataKey={type}
                name={formatDifficultyLabel(type)}
                fill={fillForDifficultyType(type, i)}
                radius={[3, 3, 0, 0]}
              />
            ))}
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

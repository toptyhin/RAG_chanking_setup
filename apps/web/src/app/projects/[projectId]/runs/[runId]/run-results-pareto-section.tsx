"use client";

import dynamic from "next/dynamic";
import { Section } from "@/components/ui";
import { useI18n } from "@/lib/locale";
import type { ParetoPoint } from "@/lib/types";

const RunResultsParetoChart = dynamic(
  () =>
    import("./run-results-pareto-chart").then((m) => m.RunResultsParetoChart),
  { ssr: false },
);

type RunResultsParetoSectionProps = {
  chartData: Array<{
    name: string;
    recall: number;
    latency: number;
    size: number;
  }>;
  pareto: ParetoPoint[];
};

export function RunResultsParetoSection({ chartData, pareto }: RunResultsParetoSectionProps) {
  const { t } = useI18n();

  return (
    <Section title={t("runPage.paretoTitle")} description={t("runPage.paretoDescription")}>
      {chartData.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">{t("runPage.paretoEmpty")}</p>
      ) : (
        <RunResultsParetoChart chartData={chartData} />
      )}
      {pareto.length > 0 ? (
        <ul className="mt-3 list-inside list-disc text-sm text-[var(--muted)]">
          {pareto.map((p) => (
            <li key={p.point_index}>
              #{p.point_index}: recall={p.recall.toFixed(3)}, p95=
              {p.latency_p95_ms.toFixed(1)}ms, size=
              {p.index_size_mb.toFixed(3)}
              MB
            </li>
          ))}
        </ul>
      ) : null}
    </Section>
  );
}

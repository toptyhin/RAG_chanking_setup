import { Section } from "@/components/ui";
import { formatMetricValue, isFailedRow } from "@/lib/metrics";
import { useI18n } from "@/lib/locale";
import type { MetricsRow } from "@/lib/types";
import { configLabel, metricLabel } from "./run-results-labels";

type RunResultsQualitySectionProps = {
  rows: MetricsRow[];
  best: MetricsRow | null;
  primaryKeys: string[];
  experimentStatus?: string;
};

export function RunResultsQualitySection({
  rows,
  best,
  primaryKeys,
  experimentStatus,
}: RunResultsQualitySectionProps) {
  const { t } = useI18n();
  const qualityRows = rows.filter((row) => !isFailedRow(row));

  return (
    <Section title={t("runPage.qualityTitle")} description={t("runPage.qualityDescription")}>
      <div className="mb-3 rounded-md border border-[var(--border)] bg-[var(--bg)]/40 px-3 py-2">
        <p className="text-xs font-medium text-[var(--fg)]">
          {t("runPage.metricsLegendTitle")}
        </p>
        <ul className="mt-1.5 list-none space-y-1 text-xs text-[var(--muted)]">
          <li>{t("runPage.metricsLegendRecall")}</li>
          <li>{t("runPage.metricsLegendMrr")}</li>
          <li>{t("runPage.metricsLegendNdcg")}</li>
        </ul>
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">
          {experimentStatus === "running" || experimentStatus === "pending"
            ? t("runPage.waiting")
            : t("runPage.noMetrics")}
        </p>
      ) : qualityRows.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">{t("runPage.qualityUnavailable")}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                <th className="py-2 pr-3 font-medium">#</th>
                <th className="py-2 pr-3 font-medium">{t("runPage.config")}</th>
                {primaryKeys.map((k) => (
                  <th key={k} className="py-2 pr-3 font-medium text-[var(--fg)]">
                    {metricLabel(k, t)}
                  </th>
                ))}
                <th className="py-2 pr-3 font-medium">{t("runPage.p50")}</th>
                <th className="py-2 font-medium">{t("runPage.p95")}</th>
              </tr>
            </thead>
            <tbody>
              {qualityRows.map((row) => {
                const isBest = best != null && row.point_index === best.point_index;
                return (
                  <tr
                    key={row.id}
                    className={`border-b border-[var(--border)] ${
                      isBest ? "bg-[var(--accent-soft)]" : ""
                    }`}
                  >
                    <td className="py-2 pr-3">{row.point_index}</td>
                    <td className="py-2 pr-3 font-mono text-xs">
                      {configLabel(row.config, t)}
                    </td>
                    {primaryKeys.map((k) => (
                      <td
                        key={k}
                        className={`py-2 pr-3 ${
                          k.startsWith("recall") ? "font-semibold" : ""
                        }`}
                      >
                        {formatMetricValue(row.metrics[k])}
                      </td>
                    ))}
                    <td className="py-2 pr-3">
                      {row.latency_p50_ms?.toFixed(1) ?? t("common.emDash")}
                    </td>
                    <td className="py-2">
                      {row.latency_p95_ms?.toFixed(1) ?? t("common.emDash")}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Section>
  );
}

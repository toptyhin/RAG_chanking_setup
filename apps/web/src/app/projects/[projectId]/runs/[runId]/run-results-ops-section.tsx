import { Section } from "@/components/ui";
import { formatMetricValue, isFailedRow } from "@/lib/metrics";
import { useI18n } from "@/lib/locale";
import type { MetricsRow } from "@/lib/types";
import { metricLabel } from "./run-results-labels";

type RunResultsOpsSectionProps = {
  rows: MetricsRow[];
  secondaryKeys: string[];
};

export function RunResultsOpsSection({ rows, secondaryKeys }: RunResultsOpsSectionProps) {
  const { t } = useI18n();
  const succeededRows = rows.filter((row) => !isFailedRow(row));

  if (secondaryKeys.length === 0 || succeededRows.length === 0) return null;

  return (
    <Section title={t("runPage.opsTitle")} description={t("runPage.opsDescription")}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-[var(--muted)]">
              <th className="py-2 pr-3 font-medium">#</th>
              {secondaryKeys.map((k) => (
                <th key={k} className="py-2 pr-3 font-medium">
                  {metricLabel(k, t)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {succeededRows.map((row) => (
              <tr key={row.id} className="border-b border-[var(--border)]">
                <td className="py-2 pr-3">{row.point_index}</td>
                {secondaryKeys.map((k) => (
                  <td key={k} className="py-2 pr-3">
                    {formatMetricValue(row.metrics[k])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

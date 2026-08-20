import { Button, Section } from "@/components/ui";
import { recallFromMetrics } from "@/lib/metrics";
import { useI18n } from "@/lib/locale";
import type { MetricsRow } from "@/lib/types";
import { configLabel } from "./run-results-labels";
import type { RunRecommendations } from "./use-run-results";
import { metricSize } from "./run-results-utils";

type RunResultsVerdictProps = {
  runId: string;
  evaluatesLabel: string;
  rows: MetricsRow[];
  recommendations: RunRecommendations;
};

export function RunResultsVerdict({
  runId,
  evaluatesLabel,
  rows,
  recommendations,
}: RunResultsVerdictProps) {
  const { t } = useI18n();

  function downloadDecisionSummary() {
    const chosen = recommendations.balanced ?? recommendations.quality;
    if (!chosen) return;
    const recall = recallFromMetrics(chosen.metrics);
    const text = [
      `# ${t("runPage.exportTitle")}`,
      "",
      `${t("runPage.exportRun")}: ${runId}`,
      `${t("runPage.exportRecommendation")}: ${configLabel(chosen.config, t)}`,
      `${t("runPage.bestRecall")}: ${recall?.toFixed(3) ?? "—"}`,
      `${t("runPage.p95")}: ${chosen.latency_p95_ms?.toFixed(1) ?? "—"}`,
      "",
      t("runPage.answerWarning"),
    ].join("\n");
    const url = URL.createObjectURL(
      new Blob([text], { type: "text/markdown;charset=utf-8" }),
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${evaluatesLabel}-${runId}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Section
      title={t("runPage.verdictTitle")}
      description={t("runPage.verdictPlainDescription")}
    >
      <div className="grid gap-3 lg:grid-cols-3">
        {(
          [
            ["quality", t("runPage.pickQuality"), recommendations.quality],
            ["balanced", t("runPage.pickBalanced"), recommendations.balanced],
            ["memory", t("runPage.pickMemory"), recommendations.memory],
          ] as const
        ).map(([kind, label, row]) => {
          if (!row) return null;
          const recall = recallFromMetrics(row.metrics);
          const baseline = rows[0] ? recallFromMetrics(rows[0].metrics) : null;
          const delta = recall != null && baseline != null ? recall - baseline : null;
          return (
            <article
              key={kind}
              className={`rounded-lg border p-4 ${
                kind === "balanced"
                  ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                  : "border-[var(--border)]"
              }`}
            >
              <p className="text-sm font-semibold">{label}</p>
              <p className="mt-2 text-2xl font-semibold">{recall?.toFixed(3) ?? "—"}</p>
              <p className="text-xs text-[var(--muted)]">{t("runPage.recallLabel")}</p>
              <p className="mt-2 text-xs leading-relaxed">{configLabel(row.config, t)}</p>
              <p className="mt-2 text-xs text-[var(--muted)]">
                {row.latency_p95_ms != null
                  ? t("runPage.p95Latency", { ms: row.latency_p95_ms.toFixed(1) })
                  : null}
                {metricSize(row) != null
                  ? ` · ${t("runPage.indexSize", { size: metricSize(row)!.toFixed(2) })}`
                  : null}
              </p>
              {delta != null ? (
                <p className="mt-1 text-xs text-[var(--muted)]">
                  {t("runPage.baselineDelta", {
                    delta: `${delta >= 0 ? "+" : ""}${delta.toFixed(3)}`,
                  })}
                </p>
              ) : null}
            </article>
          );
        })}
      </div>
      <p className="mt-3 text-xs text-[var(--muted)]">{t("runPage.recallExplain")}</p>
      <Button type="button" className="mt-4" onClick={downloadDecisionSummary}>
        {t("runPage.exportDecision")}
      </Button>
    </Section>
  );
}

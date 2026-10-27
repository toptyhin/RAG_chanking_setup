"use client";

import { useParams } from "next/navigation";
import { DifficultyBreakdown } from "@/components/difficulty-breakdown";
import { Section } from "@/components/ui";
import { flattenQueryTypeBreakdown } from "@/lib/query-type";
import { useI18n } from "@/lib/locale";
import { RunResultsFailureNotice } from "./run-results-failure-notice";
import { RunResultsHeader } from "./run-results-header";
import { RunResultsOpsSection } from "./run-results-ops-section";
import { RunResultsParetoSection } from "./run-results-pareto-section";
import { RunResultsQualitySection } from "./run-results-quality-section";
import { RunResultsReportSection } from "./run-results-report-section";
import { RunResultsVerdict } from "./run-results-verdict";
import { useRunResults } from "./use-run-results";

export default function RunResultsPage() {
  const { t } = useI18n();
  const params = useParams<{ projectId: string; runId: string }>();
  const { projectId, runId } = params;

  const {
    project,
    experiment,
    rows,
    best,
    bestRecall,
    failedPoints,
    hasSuccessfulPoints,
    primaryKeys,
    secondaryKeys,
    progress,
    pareto,
    chartData,
    recommendations,
  } = useRunResults(projectId, runId);

  return (
    <div>
      <RunResultsHeader
        projectId={projectId}
        projectName={project.data?.name}
        experiment={experiment.data}
        progress={progress}
        isLoading={experiment.isLoading}
        isError={experiment.isError}
        error={experiment.error as Error | null}
      />

      <RunResultsFailureNotice
        experiment={experiment.data}
        rows={rows}
        failedPoints={failedPoints}
      />

      {best && bestRecall != null && experiment.data?.status === "completed" ? (
        <RunResultsVerdict
          runId={runId}
          evaluatesLabel={experiment.data.evaluates ?? "lab"}
          rows={rows}
          recommendations={recommendations}
        />
      ) : null}

      <RunResultsQualitySection
        rows={rows}
        best={best}
        primaryKeys={primaryKeys}
        experimentStatus={experiment.data?.status}
      />

      {rows.some((r) => flattenQueryTypeBreakdown(r.metrics).length > 0) ? (
        <Section
          title={t("runPage.byTypeTitle")}
          description={t("runPage.byTypeDescription")}
        >
          <DifficultyBreakdown rows={rows} />
        </Section>
      ) : null}

      <RunResultsOpsSection rows={rows} secondaryKeys={secondaryKeys} />

      {rows.length === 0 || hasSuccessfulPoints ? (
        <RunResultsParetoSection chartData={chartData} pareto={pareto} />
      ) : null}

      {rows.length === 0 || hasSuccessfulPoints ? (
        <RunResultsReportSection
          runId={runId}
          reportObjectKey={experiment.data?.report_object_key}
        />
      ) : null}
    </div>
  );
}

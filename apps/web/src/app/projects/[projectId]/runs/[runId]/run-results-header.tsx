import Link from "next/link";
import { Callout, ErrorBox } from "@/components/ui";
import { useI18n } from "@/lib/locale";
import type { Experiment, Progress } from "@/lib/types";
import {
  configLabel,
  modeLabel,
  scopeLabel,
  statusLabel,
} from "./run-results-labels";

type RunResultsHeaderProps = {
  projectId: string;
  projectName?: string;
  experiment: Experiment | undefined;
  progress: Progress | null | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
};

export function RunResultsHeader({
  projectId,
  projectName,
  experiment,
  progress,
  isLoading,
  isError,
  error,
}: RunResultsHeaderProps) {
  const { t } = useI18n();

  return (
    <>
      <p className="text-sm text-[var(--muted)]">
        <Link href="/projects">{t("common.projects")}</Link> /{" "}
        <Link href={`/projects/${projectId}`}>{projectName ?? projectId}</Link> /{" "}
        {t("common.run")}
      </p>
      <div className="mb-2 flex items-center gap-2">
        <Link
          href={`/projects/${projectId}/results`}
          className="inline-flex size-8 shrink-0 items-center justify-center rounded-md text-[var(--muted)] no-underline hover:bg-[var(--accent-soft)] hover:text-[var(--fg)] hover:no-underline focus:no-underline active:no-underline"
          aria-label={t("common.back")}
          title={t("common.back")}
        >
          <svg
            aria-hidden
            viewBox="0 0 16 16"
            className="size-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M10 3 5 8l5 5" />
          </svg>
        </Link>
        <h1 className="text-xl font-semibold leading-8">
          {experiment
            ? t("runPage.titleForMode", { mode: modeLabel(experiment.evaluates, t) })
            : t("runPage.title")}
        </h1>
      </div>
      {experiment ? (
        <p className="mb-2 text-sm text-[var(--muted)]">
          {t("runPage.status")}{" "}
          <strong>{statusLabel(experiment.status, t)}</strong>
          {experiment.evaluates ? ` · ${modeLabel(experiment.evaluates, t)}` : null}
          {experiment.error ? ` — ${experiment.error}` : null}
        </p>
      ) : null}

      {progress && progress.total > 0 ? (
        <p className="mb-4 text-sm">
          {t("runPage.progress")}{" "}
          <strong>
            {progress.done}/{progress.total} {t("runPage.configs")}
          </strong>{" "}
          ({progress.percent.toFixed(0)}%)
          {progress.current_config ? (
            <span className="ml-2 text-xs text-[var(--muted)]">
              {configLabel(progress.current_config, t)}
            </span>
          ) : null}
        </p>
      ) : null}

      {experiment?.disclaimer ? (
        <div className="mb-6 border-l-4 border-[var(--warn-border)] bg-[var(--warn-bg)] px-3 py-2 text-sm text-[var(--warn)]">
          {scopeLabel(experiment.evaluates, t)}
        </div>
      ) : null}

      {!experiment || experiment.evaluates === "retrieval" ? (
        <Callout tone="warning" className="mb-6">
          <strong>{t("runPage.retrievalScopeTitle")}</strong> {t("runPage.answerWarning")}
        </Callout>
      ) : null}

      {isLoading ? (
        <p className="text-sm text-[var(--muted)]">{t("common.loading")}</p>
      ) : null}
      {isError && error ? <ErrorBox message={error.message} /> : null}
    </>
  );
}

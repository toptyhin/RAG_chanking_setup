"use client";

import Link from "next/link";
import { Button, ButtonLink, Callout, StatusDot } from "@/components/ui";
import { useI18n } from "@/lib/locale";

type Props = {
  projectId: string;
  chunkCount: number;
  testSetCount: number;
  runCount: number;
  demoPending: boolean;
  demoError?: string | null;
  onChooseDocuments: () => void;
  onChooseByo: () => void;
  onLoadDemo: () => void;
  onOpenData: () => void;
  onOpenTestSet: () => void;
};

export function ProjectOverview({
  projectId,
  chunkCount,
  testSetCount,
  runCount,
  demoPending,
  demoError,
  onChooseDocuments,
  onChooseByo,
  onLoadDemo,
  onOpenData,
  onOpenTestSet,
}: Props) {
  const { t } = useI18n();
  const hasChunks = chunkCount > 0;
  const hasTests = testSetCount > 0;
  const ready = hasChunks && hasTests;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 sm:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--accent)]">
          {t("overview.eyebrow")}
        </p>
        <h2 className="mt-2 max-w-2xl text-2xl font-semibold tracking-tight">
          {t("overview.title")}
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[var(--muted)]">
          {t("overview.description")}
        </p>

        {!hasChunks ? (
          <div className="mt-6">
            <h3 className="text-sm font-semibold">{t("overview.choosePath")}</h3>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <button
                type="button"
                onClick={onChooseDocuments}
                className="rounded-lg border border-[var(--border)] bg-[var(--bg)]/40 p-4 text-left transition hover:border-[var(--accent)] hover:bg-[var(--accent-soft)]"
              >
                <span className="text-xs font-semibold text-[var(--accent)]">01</span>
                <span className="mt-2 block font-medium">{t("overview.documentsTitle")}</span>
                <span className="mt-1 block text-xs leading-relaxed text-[var(--muted)]">
                  {t("overview.documentsDescription")}
                </span>
              </button>
              <button
                type="button"
                onClick={onChooseByo}
                className="rounded-lg border border-[var(--border)] bg-[var(--bg)]/40 p-4 text-left transition hover:border-[var(--accent)] hover:bg-[var(--accent-soft)]"
              >
                <span className="text-xs font-semibold text-[var(--accent)]">02</span>
                <span className="mt-2 block font-medium">{t("overview.byoTitle")}</span>
                <span className="mt-1 block text-xs leading-relaxed text-[var(--muted)]">
                  {t("overview.byoDescription")}
                </span>
              </button>
              <button
                type="button"
                onClick={onLoadDemo}
                disabled={demoPending}
                className="rounded-lg border border-[var(--border)] bg-[var(--bg)]/40 p-4 text-left transition hover:border-[var(--accent)] hover:bg-[var(--accent-soft)] disabled:opacity-50"
              >
                <span className="text-xs font-semibold text-[var(--accent)]">03</span>
                <span className="mt-2 block font-medium">{t("overview.demoTitle")}</span>
                <span className="mt-1 block text-xs leading-relaxed text-[var(--muted)]">
                  {demoPending ? t("overview.demoLoading") : t("overview.demoDescription")}
                </span>
              </button>
            </div>
            {demoError ? <Callout tone="warning" className="mt-3">{demoError}</Callout> : null}
          </div>
        ) : null}
      </section>

      <section className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">{t("overview.progressTitle")}</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">{t("overview.progressDescription")}</p>
          </div>
          <span className="text-sm font-medium text-[var(--accent)]">
            {[hasChunks, hasTests, runCount > 0].filter(Boolean).length}/3
          </span>
        </div>
        <ol className="mt-4 grid gap-3 md:grid-cols-3">
          <li className="rounded-lg border border-[var(--border)] p-3">
            <StatusDot ok={hasChunks} label={t(hasChunks ? "overview.dataReady" : "overview.dataMissing")} />
            <p className="mt-2 text-xs text-[var(--muted)]">
              {hasChunks ? t("overview.fragmentsCount", { count: chunkCount }) : t("overview.dataHint")}
            </p>
          </li>
          <li className="rounded-lg border border-[var(--border)] p-3">
            <StatusDot ok={hasTests} label={t(hasTests ? "overview.testsReady" : "overview.testsMissing")} />
            <p className="mt-2 text-xs text-[var(--muted)]">
              {hasTests ? t("overview.testSetsCount", { count: testSetCount }) : t("overview.testsHint")}
            </p>
          </li>
          <li className="rounded-lg border border-[var(--border)] p-3">
            <StatusDot ok={runCount > 0} label={t(runCount > 0 ? "overview.resultsReady" : "overview.resultsMissing")} />
            <p className="mt-2 text-xs text-[var(--muted)]">
              {runCount > 0 ? t("overview.runsCount", { count: runCount }) : t("overview.resultsHint")}
            </p>
          </li>
        </ol>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          {!hasChunks ? (
            <Button type="button" onClick={onOpenData}>{t("overview.addData")}</Button>
          ) : !hasTests ? (
            <Button type="button" onClick={onOpenTestSet}>{t("overview.prepareTests")}</Button>
          ) : (
            <ButtonLink href={`/projects/${projectId}/runs/new`}>
              {t("overview.startRetrievalLab")}
            </ButtonLink>
          )}
          {ready ? (
            <span className="text-xs text-[var(--muted)]">{t("overview.scopeNote")}</span>
          ) : null}
        </div>
      </section>

      <p className="text-sm text-[var(--muted)]">
        {t("overview.newToRag")}{" "}
        <Link href="/learn" className="font-medium text-[var(--accent)] underline">
          {t("overview.learnLink")}
        </Link>
      </p>
    </div>
  );
}

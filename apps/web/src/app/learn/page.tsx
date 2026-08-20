"use client";

import Link from "next/link";
import { Callout, GlossaryTerm, Section } from "@/components/ui";
import { useI18n } from "@/lib/locale";

export default function LearnPage() {
  const { t } = useI18n();
  return (
    <main>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--accent)]">
        {t("learn.eyebrow")}
      </p>
      <h1 className="mt-2 text-2xl font-semibold">{t("learn.title")}</h1>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[var(--muted)]">
        {t("learn.intro")}
      </p>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Section title={t("learn.ragTitle")} description={t("learn.ragDescription")}>
          <ol className="space-y-3 text-sm">
            <li><strong>1.</strong> {t("learn.stepFind")}</li>
            <li><strong>2.</strong> {t("learn.stepContext")}</li>
            <li><strong>3.</strong> {t("learn.stepAnswer")}</li>
          </ol>
        </Section>
        <Section title={t("learn.labTitle")} description={t("learn.labDescription")}>
          <ul className="space-y-3 text-sm">
            <li><strong>{t("learn.prepLab")}:</strong> {t("learn.prepLabText")}</li>
            <li><strong>{t("learn.chunkLab")}:</strong> {t("learn.chunkLabText")}</li>
            <li><strong>{t("learn.retrievalLab")}:</strong> {t("learn.retrievalLabText")}</li>
          </ul>
        </Section>
      </div>

      <Section title={t("learn.metricsTitle")} description={t("learn.metricsDescription")}>
        <div className="grid gap-3 md:grid-cols-3">
          <p className="rounded-lg border border-[var(--border)] p-3 text-sm">
            <GlossaryTerm definition={t("learn.recallDefinition")}>Recall@k</GlossaryTerm>
            <span className="mt-2 block text-xs text-[var(--muted)]">{t("learn.recallMeaning")}</span>
          </p>
          <p className="rounded-lg border border-[var(--border)] p-3 text-sm">
            <GlossaryTerm definition={t("learn.latencyDefinition")}>{t("learn.latency")}</GlossaryTerm>
            <span className="mt-2 block text-xs text-[var(--muted)]">{t("learn.latencyMeaning")}</span>
          </p>
          <p className="rounded-lg border border-[var(--border)] p-3 text-sm">
            <GlossaryTerm definition={t("learn.paretoDefinition")}>Pareto</GlossaryTerm>
            <span className="mt-2 block text-xs text-[var(--muted)]">{t("learn.paretoMeaning")}</span>
          </p>
        </div>
      </Section>

      <Callout tone="warning">{t("learn.recallWarning")}</Callout>
      <Link
        href="/projects"
        className="mt-5 inline-flex rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-medium text-[var(--accent-fg)]"
      >
        {t("learn.openProjects")}
      </Link>
    </main>
  );
}

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useI18n } from "@/lib/locale";
import { LabModePicker } from "./lab-mode-picker";
import { NewRunExperimentForm } from "./new-run-experiment-form";
import { NewRunNotReadySection } from "./new-run-not-ready-section";
import { useNewRunForm } from "./use-new-run-form";

export default function NewRunPage() {
  const { t } = useI18n();
  const params = useParams<{ projectId: string }>();
  const projectId = params.projectId;
  const form = useNewRunForm(projectId);

  return (
    <div>
      <p className="text-sm text-[var(--muted)]">
        <Link href="/projects">{t("common.projects")}</Link> /{" "}
        <Link href={`/projects/${projectId}`}>
          {form.project.data?.name ?? projectId}
        </Link>{" "}
        / {t("common.evaluate")}
      </p>
      <div className="mb-2 flex items-center gap-2">
        <Link
          href={`/projects/${projectId}/labs`}
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
        <h1 className="text-xl font-semibold leading-8">{t("newRunPage.title")}</h1>
      </div>
      <p className="mb-6 max-w-2xl text-sm text-[var(--muted)]">{t("newRunPage.intro")}</p>

      <LabModePicker labMode={form.labMode} onLabModeChange={form.setLabMode} />

      {!form.ready ? (
        <NewRunNotReadySection
          projectId={projectId}
          labMode={form.labMode}
          hasStartArtifact={form.hasStartArtifact}
          testSetCount={form.testSets.length}
          emptyChunkSets={form.emptyChunkSets}
        />
      ) : (
        <NewRunExperimentForm form={form} />
      )}
    </div>
  );
}

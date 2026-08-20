import Link from "next/link";
import { ButtonLink, Section, StatusDot } from "@/components/ui";
import { useI18n } from "@/lib/locale";
import type { ProjectWorkspaceState } from "./use-project-workspace";

type ProjectLabsTabProps = {
  workspace: ProjectWorkspaceState;
};

export function ProjectLabsTab({ workspace }: ProjectLabsTabProps) {
  const { t } = useI18n();
  const {
    projectId,
    rawBundles,
    hasTestSet,
    cleanCorpora,
    hasChunks,
    anyLabReady,
  } = workspace;

  return (
    <Section
      title={t("projectPage.readyTitle")}
      description={t("projectPage.readyDescription")}
    >
      <div className="grid gap-3 sm:grid-cols-3">
        {(
          [
            {
              key: "prep",
              ready: rawBundles.length > 0 && hasTestSet,
              title: t("newRunPage.prepLab"),
              description: t("newRunPage.prepLabDescription"),
            },
            {
              key: "chunk",
              ready: cleanCorpora.length > 0 && hasTestSet,
              title: t("newRunPage.chunkLab"),
              description: t("newRunPage.chunkLabDescription"),
            },
            {
              key: "retrieval",
              ready: hasChunks && hasTestSet,
              title: t("newRunPage.retrievalLab"),
              description: t("newRunPage.retrievalLabDescription"),
            },
          ] as const
        ).map((lab) => (
          <article
            key={lab.key}
            className="rounded-md border border-[var(--border)] bg-[var(--bg)]/60 px-3 py-3"
          >
            <StatusDot
              ok={lab.ready}
              label={
                lab.ready
                  ? t("projectPage.labReady")
                  : t("projectPage.labBlocked")
              }
            />
            <h3 className="mt-2 text-sm font-semibold">{lab.title}</h3>
            <p className="mt-1 text-xs text-[var(--muted)]">{lab.description}</p>
          </article>
        ))}
      </div>
      {!hasTestSet ? (
        <p className="mt-3 text-sm text-[var(--muted)]">
          {t("projectPage.labelsHint")}{" "}
          <Link
            href={`/projects/${projectId}/test-set`}
            className="text-[var(--accent)] underline"
          >
            {t("projectPage.tabTestSet")}
          </Link>
        </p>
      ) : null}
      <div className="mt-4">
        <ButtonLink
          href={`/projects/${projectId}/runs/new`}
          disabled={!anyLabReady}
        >
          {t("projectPage.evaluateRetrieval")}
        </ButtonLink>
      </div>
    </Section>
  );
}

import Link from "next/link";
import { Section } from "@/components/ui";
import { artifactDisplayName, chunkSetEmptyReason } from "@/lib/format";
import { useI18n } from "@/lib/locale";
import type { Artifact } from "@/lib/types";
import type { LabMode } from "./new-run-utils";

type NewRunNotReadySectionProps = {
  projectId: string;
  labMode: LabMode;
  hasStartArtifact: boolean;
  testSetCount: number;
  emptyChunkSets: Artifact[];
};

export function NewRunNotReadySection({
  projectId,
  labMode,
  hasStartArtifact,
  testSetCount,
  emptyChunkSets,
}: NewRunNotReadySectionProps) {
  const { t } = useI18n();

  return (
    <Section
      title={t("newRunPage.notReadyTitle")}
      description={t("newRunPage.notReadyDescription")}
    >
      <p className="text-sm text-[var(--muted)]">
        {!hasStartArtifact
          ? `${
              labMode === "prep"
                ? t("newRunPage.needRawBundle")
                : labMode === "chunk"
                  ? t("newRunPage.needCleanCorpus")
                  : t("newRunPage.needChunkSet")
            } `
          : null}
        {!testSetCount ? `${t("newRunPage.needTestSet")} ` : null}
        <Link
          href={
            !hasStartArtifact
              ? `/projects/${projectId}/data`
              : `/projects/${projectId}/test-set`
          }
          className="text-[var(--accent)] underline"
        >
          {t("newRunPage.backChecklist")}
        </Link>
      </p>
      {emptyChunkSets.length > 0 ? (
        <div className="mt-3 space-y-1 text-sm text-[var(--danger,#b42318)]">
          {emptyChunkSets.map((a) => (
            <p key={a.id}>
              <code>{artifactDisplayName(a.type, a.meta, a.id)}</code>
              {" — "}
              {chunkSetEmptyReason(a.meta) ?? "0 chunks"}
            </p>
          ))}
        </div>
      ) : null}
    </Section>
  );
}

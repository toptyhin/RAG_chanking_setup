import type { TranslationKey } from "@/i18n";
import { useI18n } from "@/lib/locale";
import type { ProjectWorkspaceState } from "./use-project-workspace";

type ProjectTestQualityCardsProps = {
  workspace: ProjectWorkspaceState;
};

export function ProjectTestQualityCards({
  workspace,
}: ProjectTestQualityCardsProps) {
  const { t } = useI18n();
  const { hasTestSet, testQuality } = workspace;

  if (!hasTestSet) return null;

  return (
    <div className="mb-4 grid gap-2 sm:grid-cols-3">
      <div className="rounded-md border border-[var(--border)] p-3">
        <p className="text-xs text-[var(--muted)]">
          {t("projectPage.testQualitySource")}
        </p>
        <p className="mt-1 text-sm font-medium">
          {t(
            `projectPage.testQualitySource${testQuality.source === "synthetic" ? "Synthetic" : testQuality.source === "manual" ? "Manual" : testQuality.source === "imported" ? "Imported" : testQuality.source === "mixed" ? "Mixed" : "Unknown"}` as TranslationKey,
          )}
        </p>
      </div>
      <div className="rounded-md border border-[var(--border)] p-3">
        <p className="text-xs text-[var(--muted)]">
          {t("projectPage.testQualityReviewed")}
        </p>
        <p className="mt-1 text-sm font-medium">
          {t("projectPage.testQualityReviewedCount", {
            reviewed: testQuality.reviewed,
            total: testQuality.total,
          })}
        </p>
      </div>
      <div className="rounded-md border border-[var(--border)] p-3">
        <p className="text-xs text-[var(--muted)]">
          {t("projectPage.testQualityCoverage")}
        </p>
        <p className="mt-1 text-sm font-medium">
          {t("projectPage.testQualityLevels", { count: testQuality.levels })}
        </p>
      </div>
    </div>
  );
}

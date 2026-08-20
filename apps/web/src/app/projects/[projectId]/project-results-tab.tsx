import Link from "next/link";
import { RunComparison } from "@/components/run-comparison";
import { Button, ErrorBox, Section } from "@/components/ui";
import { shortId } from "@/lib/format";
import { useI18n } from "@/lib/locale";
import type { ProjectWorkspaceState } from "./use-project-workspace";

type ProjectResultsTabProps = {
  workspace: ProjectWorkspaceState;
};

export function ProjectResultsTab({ workspace }: ProjectResultsTabProps) {
  const { t } = useI18n();
  const { projectId, experiments, setActiveTab } = workspace;

  return (
    <div>
      <Section
        title={t("projectPage.recentRunsTitle")}
        description={t("projectPage.recentRunsDescription")}
      >
        {experiments.isLoading ? (
          <p className="text-sm text-[var(--muted)]">{t("common.loading")}</p>
        ) : null}
        {experiments.isError ? (
          <ErrorBox message={(experiments.error as Error).message} />
        ) : null}
        {(experiments.data ?? []).length === 0 ? (
          <div className="space-y-3">
            <p className="text-sm text-[var(--muted)]">
              {t("projectPage.noRuns")}
            </p>
            <Button
              type="button"
              className="bg-transparent text-[var(--fg)] ring-1 ring-[var(--border)]"
              onClick={() => setActiveTab("labs")}
            >
              {t("projectNav.labs")}
            </Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                  <th className="py-2 pr-3 font-medium">
                    {t("projectPage.tableRun")}
                  </th>
                  <th className="py-2 pr-3 font-medium">
                    {t("projectPage.tableMode")}
                  </th>
                  <th className="py-2 pr-3 font-medium">
                    {t("projectPage.tableStatus")}
                  </th>
                  <th className="py-2 font-medium" />
                </tr>
              </thead>
              <tbody>
                {(experiments.data ?? []).map((run) => (
                  <tr
                    key={run.id}
                    className="border-b border-[var(--border)]"
                  >
                    <td className="py-2 pr-3">
                      <code className="text-xs">{shortId(run.id)}</code>
                    </td>
                    <td className="py-2 pr-3">{run.evaluates}</td>
                    <td className="py-2 pr-3">{run.status}</td>
                    <td className="py-2 text-right">
                      <Link
                        href={`/projects/${projectId}/runs/${run.id}`}
                        className="text-[var(--accent)] underline"
                      >
                        {t("common.open")}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
      <Section
        title={t("compare.title")}
        description={t("compare.description")}
      >
        <RunComparison projectId={projectId} runs={experiments.data ?? []} />
      </Section>
    </div>
  );
}

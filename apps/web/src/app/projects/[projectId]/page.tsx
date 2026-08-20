"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ProjectOverview } from "@/components/project-overview";
import { ProjectNav, type ProjectStage } from "@/components/project-nav";
import { ErrorBox } from "@/components/ui";
import { useI18n } from "@/lib/locale";
import { ProjectDataTab } from "./project-data-tab";
import { ProjectLabsTab } from "./project-labs-tab";
import { ProjectResultsTab } from "./project-results-tab";
import { ProjectTestTab } from "./project-test-tab";
import { useProjectWorkspace } from "./use-project-workspace";

export function ProjectWorkspace({
  initialStage,
}: {
  initialStage: ProjectStage;
}) {
  const { t } = useI18n();
  const params = useParams<{ projectId: string }>();
  const projectId = params.projectId;
  const workspace = useProjectWorkspace(initialStage);
  const { project, activeTab, setActiveTab, sample } = workspace;

  if (project.isError) {
    return <ErrorBox message={(project.error as Error).message} />;
  }

  return (
    <div>
      <div className="mb-6">
        <p className="text-sm text-[var(--muted)]">
          <Link href="/projects">{t("common.projects")}</Link> /
        </p>
        <div>
          <h1 className="text-xl font-semibold">
            {project.data?.name ?? "…"}
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--muted)]">
            {t("projectPage.intro")}
          </p>
        </div>
      </div>

      <ProjectNav projectId={projectId} value={activeTab} />

      {activeTab === "overview" ? (
        <ProjectOverview
          projectId={projectId}
          chunkCount={workspace.totalChunks}
          testSetCount={workspace.testSets.length}
          runCount={(workspace.experiments.data ?? []).length}
          demoPending={sample.isPending}
          demoError={sample.isError ? (sample.error as Error).message : null}
          onChooseDocuments={() => {
            workspace.setDataPath("documents");
            setActiveTab("data");
          }}
          onChooseByo={() => {
            workspace.setDataPath("byo");
            setActiveTab("data");
          }}
          onLoadDemo={() => sample.mutate()}
          onOpenData={() => setActiveTab("data")}
          onOpenTestSet={() => setActiveTab("test")}
        />
      ) : null}

      {activeTab === "results" ? (
        <ProjectResultsTab workspace={workspace} />
      ) : null}

      {activeTab === "data" ? <ProjectDataTab workspace={workspace} /> : null}

      {activeTab === "labs" || activeTab === "test" ? (
        <div>
          {activeTab === "labs" ? (
            <ProjectLabsTab workspace={workspace} />
          ) : null}
          {activeTab === "test" ? (
            <ProjectTestTab workspace={workspace} />
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export default function ProjectDetailPage() {
  return <ProjectWorkspace initialStage="overview" />;
}

import { Button, Section } from "@/components/ui";
import { useI18n } from "@/lib/locale";
import { ProjectTestDraftEditor } from "./project-test-draft-editor";
import { ProjectTestPrepareControls } from "./project-test-prepare-controls";
import { ProjectTestQualityCards } from "./project-test-quality-cards";
import { ProjectTestReadyQuestions } from "./project-test-ready-questions";
import type { ProjectWorkspaceState } from "./use-project-workspace";

type ProjectTestTabProps = {
  workspace: ProjectWorkspaceState;
};

export function ProjectTestTab({ workspace }: ProjectTestTabProps) {
  const { t } = useI18n();
  const {
    hasChunks,
    setActiveTab,
    labelChunkSetId,
    usableChunkSets,
    chunkPreview,
    loadChunksForLabels,
    setShowManualEditor,
    setDraftOpen,
    setQueries,
  } = workspace;

  return (
    <Section
      title={t("projectPage.goldenTitle")}
      description={t("projectPage.goldenDescription")}
    >
      <ProjectTestQualityCards workspace={workspace} />
      {!hasChunks ? (
        <p className="text-sm text-[var(--muted)]">
          {t("projectPage.needChunkSetFirst")}{" "}
          <button
            type="button"
            className="text-[var(--accent)] underline"
            onClick={() => setActiveTab("data")}
          >
            {t("projectPage.tabData")}
          </button>
        </p>
      ) : (
        <div className="grid gap-4">
          <ProjectTestPrepareControls workspace={workspace} />
          <ProjectTestReadyQuestions workspace={workspace} />
          <ProjectTestDraftEditor workspace={workspace} />
          <div>
            <Button
              type="button"
              className="bg-transparent text-[var(--fg)] ring-1 ring-[var(--border)]"
              onClick={() => {
                setShowManualEditor(true);
                setDraftOpen(true);
                setQueries((prev) =>
                  prev.length === 0
                    ? [{ text: "", relevant: [], source: "manual" }]
                    : [...prev, { text: "", relevant: [], source: "manual" }],
                );
                const id = labelChunkSetId || usableChunkSets[0]?.id;
                if (id && chunkPreview.length === 0) {
                  void loadChunksForLabels(id);
                }
              }}
            >
              {t("projectPage.addQuestion")}
            </Button>
          </div>
        </div>
      )}
    </Section>
  );
}

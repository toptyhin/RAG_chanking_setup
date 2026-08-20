import { EvidencePicker } from "@/components/evidence-picker";
import { DifficultyBadge } from "@/components/difficulty-badge";
import { Button, Input } from "@/components/ui";
import {
  evidenceLevelOf,
  minEvidenceChunks,
  needsEvidenceReview,
} from "@/lib/evidence-level";
import { useI18n } from "@/lib/locale";
import {
  evidenceHintKey,
  evidenceTitleKey,
} from "./project-workspace-utils";
import type { ProjectWorkspaceState } from "./use-project-workspace";

type ProjectTestDraftEditorProps = {
  workspace: ProjectWorkspaceState;
};

export function ProjectTestDraftEditor({ workspace }: ProjectTestDraftEditorProps) {
  const { t } = useI18n();
  const {
    projectId,
    labelChunkSetId,
    usableChunkSets,
    labelCleanCorpusId,
    prepareCleanCorpusId,
    queries,
    setQueries,
    draftOpen,
    setDraftOpen,
    chunkPreview,
    testImport,
  } = workspace;

  if (queries.length === 0) return null;

  return (
    <details
      open={draftOpen}
      onToggle={(e) =>
        setDraftOpen((e.target as HTMLDetailsElement).open)
      }
      className="rounded-md border border-[var(--border)] px-3 py-2"
    >
      <summary className="cursor-pointer text-sm font-medium">
        {t("projectPage.draftQuestionsTitle", {
          count: queries.length,
        })}
      </summary>
      <p className="mt-1 text-xs text-[var(--muted)]">
        {t("projectPage.draftQuestionsHint")}
      </p>
      <div className="mt-3 space-y-4">
        {queries.map((q, qi) => {
          const level = evidenceLevelOf(q.level, q.queryType);
          const review = needsEvidenceReview(level);
          const minChunks = minEvidenceChunks(level);
          const hintKey = evidenceHintKey(level);
          const chunkSetId = labelChunkSetId || usableChunkSets[0]?.id || "";
          return (
            <div
              key={qi}
              className="rounded-md border border-[var(--border)] p-3"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2">
                  <span className="text-sm font-medium">
                    {t("projectPage.questionN", { n: qi + 1 })}
                  </span>
                  {q.level || q.queryType ? (
                    <DifficultyBadge
                      level={q.level}
                      queryType={q.queryType}
                      showShort
                    />
                  ) : null}
                </div>
                {queries.length > 1 ? (
                  <button
                    type="button"
                    className="text-xs text-[var(--muted)] underline"
                    onClick={() =>
                      setQueries((prev) => prev.filter((_, i) => i !== qi))
                    }
                  >
                    {t("projectPage.remove")}
                  </button>
                ) : null}
              </div>
              <Input
                className="mt-1"
                placeholder={t("projectPage.questionPlaceholder")}
                value={q.text}
                onChange={(e) =>
                  setQueries((prev) =>
                    prev.map((row, i) =>
                      i === qi ? { ...row, text: e.target.value } : row,
                    ),
                  )
                }
              />
              {q.expectedAnswer ? (
                <p className="mt-2 text-xs text-[var(--muted)]">
                  {t("projectPage.expectedAnswer")}: {q.expectedAnswer}
                </p>
              ) : null}
              {q.sourceQuote ? (
                <p className="mt-1 text-xs text-[var(--muted)]">
                  {t("projectPage.sourceQuote")}: {q.sourceQuote}
                </p>
              ) : null}
              <p className="mb-1 mt-3 text-xs font-medium text-[var(--muted)]">
                {t(evidenceTitleKey(level))}
                {review ? (
                  <span className="ml-1 font-normal">
                    ({t("projectPage.evidenceMin", { n: minChunks })})
                  </span>
                ) : null}
              </p>
              {hintKey ? (
                <p className="mb-2 text-xs text-[var(--muted)]">
                  {t(hintKey)}
                </p>
              ) : null}
              {level === "l4" && q.relevant.length === 1 ? (
                <p className="mb-2 text-xs text-amber-700 dark:text-amber-400">
                  {t("projectPage.evidenceL4SingleWarn")}
                </p>
              ) : null}
              {!chunkSetId || chunkPreview.length === 0 ? (
                <p className="text-xs text-[var(--muted)]">
                  {t("projectPage.loadChunksHint")}
                </p>
              ) : (
                <EvidencePicker
                  projectId={projectId}
                  chunkSetId={chunkSetId}
                  cleanCorpusId={
                    labelCleanCorpusId || prepareCleanCorpusId || null
                  }
                  question={q.text}
                  expectedAnswer={q.expectedAnswer}
                  sourceQuote={q.sourceQuote}
                  evidenceQuotes={q.evidenceQuotes}
                  queryType={q.queryType}
                  level={q.level}
                  review={review}
                  relevant={q.relevant}
                  grades={q.grades}
                  spans={q.spans}
                  allChunks={chunkPreview}
                  onChange={(next) =>
                    setQueries((prev) =>
                      prev.map((row, i) =>
                        i === qi
                          ? {
                              ...row,
                              relevant: next.relevant,
                              grades: next.grades,
                              spans: next.spans,
                            }
                          : row,
                      ),
                    )
                  }
                />
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-3">
        <Button
          type="button"
          disabled={testImport.isPending}
          onClick={() => testImport.mutate()}
        >
          {testImport.isPending
            ? t("projectPage.saving")
            : t("projectPage.saveTestSet")}
        </Button>
      </div>
    </details>
  );
}

import Link from "next/link";
import { DifficultyBadge } from "@/components/difficulty-badge";
import { ErrorBox } from "@/components/ui";
import { resolveQueryType } from "@/lib/query-type";
import { useI18n } from "@/lib/locale";
import { RelevantChunkPreview } from "./relevant-chunk-preview";
import type { ProjectWorkspaceState } from "./use-project-workspace";

type ProjectTestReadyQuestionsProps = {
  workspace: ProjectWorkspaceState;
};

export function ProjectTestReadyQuestions({
  workspace,
}: ProjectTestReadyQuestionsProps) {
  const { t } = useI18n();
  const {
    projectId,
    hasTestSet,
    artifactLabel,
    readyTestQuestions,
  } = workspace;

  return (
    <div>
      <p className="mb-1 text-sm font-medium">
        {t("projectPage.readyQuestionsTitle")}
      </p>
      <p className="mb-2 text-xs text-[var(--muted)]">
        {t("projectPage.readyQuestionsHint")}
      </p>
      {!hasTestSet ? (
        <p className="text-sm text-[var(--muted)]">
          {t("projectPage.readyQuestionsEmpty")}
        </p>
      ) : readyTestQuestions.isLoading ? (
        <p className="text-sm text-[var(--muted)]">{t("common.loading")}</p>
      ) : readyTestQuestions.isError ? (
        <ErrorBox message={(readyTestQuestions.error as Error).message} />
      ) : (
        <div className="space-y-2">
          {(readyTestQuestions.data?.rows ?? []).map(({ artifact, content }) => {
            const qs = content.queries ?? [];
            const texts = readyTestQuestions.data?.chunkTextById ?? {};
            return (
              <details
                key={artifact.id}
                className="rounded-md border border-[var(--border)] px-3 py-2"
              >
                <summary className="cursor-pointer text-sm">
                  {t("projectPage.readyQuestionsSet", {
                    name: artifactLabel(artifact),
                    count: qs.length,
                  })}
                  {" · "}
                  <Link
                    href={`/projects/${projectId}/artifacts/${artifact.id}`}
                    className="text-[var(--accent)] underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {t("common.view")}
                  </Link>
                </summary>
                <ol className="mt-2 list-decimal space-y-3 pl-5 text-sm">
                  {qs.map((q) => {
                    const answer =
                      (typeof q.expected_answer === "string" &&
                      q.expected_answer.trim()
                        ? q.expected_answer.trim()
                        : null) ||
                      (typeof q.meta?.expected_answer === "string" &&
                      q.meta.expected_answer.trim()
                        ? q.meta.expected_answer.trim()
                        : null);
                    const qtype = resolveQueryType({
                      queryType: q.query_type,
                      meta: q.meta,
                    });
                    const levelRaw =
                      (typeof q.meta?.level === "string"
                        ? q.meta.level
                        : null) || qtype;
                    return (
                      <li key={q.query_id} className="pl-1">
                        <p className="flex flex-wrap items-baseline gap-2">
                          <span className="text-xs font-medium text-[var(--muted)]">
                            {t("projectPage.readyQuestionLabel")}:
                          </span>
                          <span>{q.text}</span>
                          {levelRaw ? (
                            <DifficultyBadge
                              level={
                                typeof q.meta?.level === "string"
                                  ? q.meta.level
                                  : undefined
                              }
                              queryType={qtype}
                            />
                          ) : null}
                        </p>
                        <p className="mt-1">
                          <span className="text-xs font-medium text-[var(--muted)]">
                            {t("projectPage.readyAnswerLabel")}:{" "}
                          </span>
                          {answer ?? (
                            <span className="text-[var(--muted)]">
                              {t("projectPage.readyAnswerMissing")}
                            </span>
                          )}
                        </p>
                        {q.relevant_chunk_ids?.length ? (
                          <div className="mt-2 space-y-1">
                            {q.relevant_chunk_ids.map((cid) => (
                              <RelevantChunkPreview
                                key={cid}
                                chunkId={cid}
                                text={texts[cid]}
                                missingLabel={t("projectPage.chunkPreviewMissing")}
                              />
                            ))}
                          </div>
                        ) : null}
                      </li>
                    );
                  })}
                </ol>
              </details>
            );
          })}
        </div>
      )}
    </div>
  );
}

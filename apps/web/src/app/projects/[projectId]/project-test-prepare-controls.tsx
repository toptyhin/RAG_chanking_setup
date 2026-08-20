import Link from "next/link";
import { DifficultyLegendRow } from "@/components/difficulty-badge";
import { Button, ErrorBox, Label, Select } from "@/components/ui";
import { artifactDisplayName } from "@/lib/format";
import { useI18n } from "@/lib/locale";
import { withReturnTo } from "@/lib/return-to";
import type { ProjectWorkspaceState } from "./use-project-workspace";

type ProjectTestPrepareControlsProps = {
  workspace: ProjectWorkspaceState;
};

export function ProjectTestPrepareControls({
  workspace,
}: ProjectTestPrepareControlsProps) {
  const { t } = useI18n();
  const {
    projectId,
    pathname,
    hasTestSet,
    usableChunkSets,
    labelChunkSetId,
    loadChunksForLabels,
    chunkPreview,
    chunkLoadError,
    cleanCorpora,
    artifactLabel,
    prepareCleanCorpusId,
    setLabelCleanCorpusId,
    prepareEstimate,
    prepareQuestions,
    queries,
    testImport,
    llmModelLabel,
  } = workspace;

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <Label>{t("projectPage.chunkSetToLabel")}</Label>
          <Select
            value={labelChunkSetId || usableChunkSets[0]?.id || ""}
            onChange={(e) => void loadChunksForLabels(e.target.value)}
            onFocus={() => {
              const id = labelChunkSetId || usableChunkSets[0]?.id;
              if (id && chunkPreview.length === 0) {
                void loadChunksForLabels(id);
              }
            }}
          >
            {usableChunkSets.map((a) => (
              <option key={a.id} value={a.id}>
                {artifactLabel(a)}
              </option>
            ))}
          </Select>
          {chunkLoadError ? <ErrorBox message={chunkLoadError} /> : null}
        </div>
        <div>
          <Label>{t("projectPage.cleanCorpusForPrep")}</Label>
          <Select
            value={prepareCleanCorpusId}
            onChange={(e) => setLabelCleanCorpusId(e.target.value)}
            disabled={cleanCorpora.length === 0}
          >
            {cleanCorpora.length === 0 ? (
              <option value="">{t("projectPage.noCleanCorpus")}</option>
            ) : null}
            {cleanCorpora.map((a) => (
              <option key={a.id} value={a.id}>
                {artifactLabel(a)}
              </option>
            ))}
          </Select>
          <p className="mt-1 text-xs text-[var(--muted)]">
            {t("projectPage.cleanCorpusForPrepHint")}
          </p>
          {prepareEstimate.isLoading ? (
            <p className="mt-2 text-xs text-[var(--muted)]">
              {t("projectPage.prepareEstimateLoading")}
            </p>
          ) : null}
          {prepareEstimate.data ? (
            <div className="mt-2 space-y-1 text-xs text-[var(--muted)]">
              <p>
                {t("projectPage.prepareContextLength", {
                  model: prepareEstimate.data.model,
                  n:
                    prepareEstimate.data.context_length != null
                      ? prepareEstimate.data.context_length.toLocaleString()
                      : t("projectPage.prepareContextUnknown"),
                })}
              </p>
              <p>
                {t("projectPage.prepareCorpusTokens", {
                  tokens:
                    prepareEstimate.data.corpus_tokens_est.toLocaleString(),
                  chars: prepareEstimate.data.corpus_chars.toLocaleString(),
                })}
              </p>
              <p>
                {t("projectPage.preparePromptTokens", {
                  tokens:
                    prepareEstimate.data.prompt_tokens_est.toLocaleString(),
                })}
              </p>
              {prepareEstimate.data.fits_context === false ? (
                <p className="text-[var(--danger)]">
                  {t("projectPage.prepareContextTooSmall")}
                </p>
              ) : null}
              {prepareEstimate.data.fits_context !== false &&
              (prepareEstimate.data.part_count ?? 1) > 1 ? (
                <p>
                  {t("projectPage.prepareContextMultipart", {
                    n: String(prepareEstimate.data.part_count ?? 1),
                  })}
                </p>
              ) : null}
              {prepareEstimate.data.fits_single_pass === true ? (
                <p>{t("projectPage.prepareContextOk")}</p>
              ) : null}
              <p className="opacity-80">
                {prepareEstimate.data.token_estimate_note}
              </p>
            </div>
          ) : null}
          {prepareEstimate.isError ? (
            <p className="mt-2 text-xs text-[var(--danger)]">
              {(prepareEstimate.error as Error).message}
            </p>
          ) : null}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          disabled={
            prepareQuestions.isPending ||
            cleanCorpora.length === 0 ||
            !prepareCleanCorpusId ||
            prepareEstimate.data?.fits_context === false
          }
          onClick={() => prepareQuestions.mutate()}
        >
          {prepareQuestions.isPending
            ? t("projectPage.preparingQuestions")
            : hasTestSet || queries.some((q) => q.text.trim().length > 0)
              ? t("projectPage.prepareQuestionsAgain")
              : t("projectPage.prepareQuestions")}
        </Button>
        {queries.length > 0 ? (
          <Button
            type="button"
            disabled={testImport.isPending}
            onClick={() => testImport.mutate()}
          >
            {testImport.isPending
              ? t("projectPage.saving")
              : t("projectPage.saveTestSet")}
          </Button>
        ) : null}
      </div>
      {llmModelLabel ? (
        <p className="text-xs text-[var(--muted)]">
          {t("projectPage.prepareUsesModel", { model: llmModelLabel })}{" "}
          <Link
            href={withReturnTo("/settings/connections?tab=questions", pathname)}
            className="text-[var(--accent)] underline"
          >
            {t("projectPage.questionConnections")}
          </Link>
        </p>
      ) : null}

      <div className="rounded-md border border-[var(--border)] bg-[var(--bg)]/40 px-3 py-2">
        <p className="text-xs font-medium text-[var(--fg)]">
          {t("projectPage.difficultyLegendTitle")}
        </p>
        <ul className="mt-1.5 list-none space-y-1 text-xs text-[var(--muted)]">
          <DifficultyLegendRow
            level="l1"
            description={t("projectPage.difficultyL1")}
          />
          <DifficultyLegendRow
            level="l2"
            description={t("projectPage.difficultyL2")}
          />
          <DifficultyLegendRow
            level="l3"
            description={t("projectPage.difficultyL3")}
          />
          <DifficultyLegendRow
            level="l4"
            description={t("projectPage.difficultyL4")}
          />
        </ul>
      </div>

      {prepareQuestions.isError ? (
        <ErrorBox message={(prepareQuestions.error as Error).message} />
      ) : null}
      {prepareQuestions.isSuccess && prepareQuestions.data ? (
        <p className="text-sm text-[var(--muted)]">
          {t("projectPage.prepareDone", {
            count: prepareQuestions.data.questions.length,
            model: `${prepareQuestions.data.provider}/${prepareQuestions.data.model}`,
            version: prepareQuestions.data.prompt_version,
          })}
        </p>
      ) : null}
      {testImport.isError ? (
        <ErrorBox message={(testImport.error as Error).message} />
      ) : null}
      {testImport.isSuccess ? (
        <p className="text-sm text-[var(--muted)]">
          {t("projectPage.savedTestSet", {
            id: artifactDisplayName(
              testImport.data.artifact.type,
              testImport.data.artifact.meta,
              testImport.data.artifact.id,
            ),
            count: testImport.data.query_count,
          })}{" "}
          <Link
            href={`/projects/${projectId}/artifacts/${testImport.data.artifact.id}`}
            className="text-[var(--accent)] underline"
          >
            {t("common.view")}
          </Link>
          {" · "}
          <Link
            href={`/projects/${projectId}/labs`}
            className="text-[var(--accent)] underline"
          >
            {t("projectPage.canEvaluate")}
          </Link>
        </p>
      ) : null}
    </>
  );
}

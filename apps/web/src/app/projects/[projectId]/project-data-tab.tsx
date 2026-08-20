import Link from "next/link";
import { ChunkerSettingsForm } from "@/components/chunker-settings-form";
import { FileDropzone } from "@/components/file-dropzone";
import { ImportArtifactsPanel } from "@/components/import-artifacts";
import { Button, ErrorBox, Label, Section, TextArea } from "@/components/ui";
import { artifactDisplayName, chunkSetEmptyReason } from "@/lib/format";
import { useI18n } from "@/lib/locale";
import type { ProjectWorkspaceState } from "./use-project-workspace";

type ProjectDataTabProps = {
  workspace: ProjectWorkspaceState;
};

export function ProjectDataTab({ workspace }: ProjectDataTabProps) {
  const { t } = useI18n();
  const {
    projectId,
    ready,
    sample,
    dataPath,
    setDataPath,
    byoJson,
    setByoJson,
    byo,
    upload,
    cleanId,
    setCleanId,
    cleanCorpora,
    chunkSets,
    artifactLabel,
    refreshAll,
    setActiveTab,
  } = workspace;

  return (
    <div>
      <Section
        title={t("projectPage.importFromProjectTitle")}
        description={t("projectPage.importFromProjectDescription")}
      >
        <ImportArtifactsPanel projectId={projectId} />
      </Section>

      <Section
        title={t("projectPage.getChunksTitle")}
        description={t("projectPage.getChunksDescription")}
      >
        {!ready ? (
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <Button
              type="button"
              disabled={sample.isPending}
              onClick={() => sample.mutate()}
            >
              {sample.isPending
                ? t("projectPage.loadingSample")
                : t("projectPage.loadSample")}
            </Button>
            <p className="text-xs text-[var(--muted)]">
              {t("projectPage.sampleHint")}
            </p>
          </div>
        ) : null}
        {sample.isError ? (
          <ErrorBox message={(sample.error as Error).message} />
        ) : null}
        {sample.isSuccess ? (
          <p className="mb-4 text-sm text-[var(--muted)]">
            {t("projectPage.sampleReady")}{" "}
            <button
              type="button"
              className="font-medium text-[var(--accent)] underline"
              onClick={() => setActiveTab("labs")}
            >
              {t("projectPage.runEvaluation")}
            </button>
            .
          </p>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => setDataPath(dataPath === "byo" ? null : "byo")}
            className={`rounded-md border px-4 py-3 text-left transition ${
              dataPath === "byo"
                ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                : "border-[var(--border)] bg-[var(--bg)]/40 hover:border-[var(--accent)]/50"
            }`}
          >
            <p className="font-medium">{t("projectPage.byoTitle")}</p>
            <p className="mt-1 text-xs text-[var(--muted)]">
              {t("projectPage.byoDescription")}
            </p>
          </button>
          <button
            type="button"
            onClick={() =>
              setDataPath(dataPath === "documents" ? null : "documents")
            }
            className={`rounded-md border px-4 py-3 text-left transition ${
              dataPath === "documents"
                ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                : "border-[var(--border)] bg-[var(--bg)]/40 hover:border-[var(--accent)]/50"
            }`}
          >
            <p className="font-medium">{t("projectPage.documentsTitle")}</p>
            <p className="mt-1 text-xs text-[var(--muted)]">
              {t("projectPage.documentsDescription")}
            </p>
          </button>
        </div>

        {dataPath === "byo" ? (
          <div className="mt-4">
            <Label>{t("projectPage.chunkSetJson")}</Label>
            <TextArea
              rows={8}
              value={byoJson}
              onChange={(e) => setByoJson(e.target.value)}
            />
            <Button
              className="mt-3"
              disabled={byo.isPending}
              onClick={() => byo.mutate()}
            >
              {byo.isPending
                ? t("projectPage.importing")
                : t("projectPage.importChunkSet")}
            </Button>
            {byo.isError ? (
              <ErrorBox message={(byo.error as Error).message} />
            ) : null}
            {byo.isSuccess ? (
              <p className="mt-2 text-sm text-[var(--muted)]">
                {t("projectPage.importedChunks", {
                  count: byo.data.chunk_count,
                  id: artifactDisplayName(
                    byo.data.artifact.type,
                    byo.data.artifact.meta,
                    byo.data.artifact.id,
                  ),
                })}{" "}
                <Link
                  href={`/projects/${projectId}/artifacts/${byo.data.artifact.id}`}
                  className="text-[var(--accent)] underline"
                >
                  {t("common.view")}
                </Link>
                {" · "}
                <Link
                  href={`/projects/${projectId}/test-set`}
                  className="text-[var(--accent)] underline"
                >
                  {t("projectPage.continueLabels")}
                </Link>
              </p>
            ) : null}
          </div>
        ) : null}

        {dataPath === "documents" ? (
          <div className="mt-4 space-y-6">
            <div>
              <FileDropzone
                disabled={upload.isPending}
                accept=".txt,.md,.markdown,.text,.pdf"
                title={t("projectPage.dropzoneTitle")}
                hint={t("projectPage.dropzoneHint")}
                busyLabel={t("projectPage.uploadingAndPrep")}
                onFiles={(files) => upload.mutate(files)}
              />
              {upload.isError ? (
                <ErrorBox message={(upload.error as Error).message} />
              ) : null}
              {upload.isSuccess ? (
                <div className="mt-3 rounded-lg border border-[var(--accent)]/40 bg-[var(--accent-soft)] p-4">
                  <p className="text-sm font-medium">
                    {t("projectPage.reviewDocumentsTitle")}
                  </p>
                  <p className="mt-1 text-sm text-[var(--muted)]">
                    {t("projectPage.uploadPrepDone", {
                      files: upload.data.files_stored,
                      docs: upload.data.document_count,
                      id: artifactDisplayName(
                        upload.data.clean_corpus.type,
                        upload.data.clean_corpus.meta,
                        upload.data.clean_corpus.id,
                      ),
                    })}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-3 text-sm">
                    <Link
                      href={`/projects/${projectId}/artifacts/${upload.data.clean_corpus.id}`}
                      className="font-medium text-[var(--accent)] underline"
                    >
                      {t("projectPage.reviewDocuments")}
                    </Link>
                    <span className="text-[var(--muted)]">
                      {t("projectPage.thenChooseChunking")}
                    </span>
                  </div>
                </div>
              ) : null}
            </div>

            <ChunkerSettingsForm
              projectId={projectId}
              cleanCorpora={cleanCorpora}
              cleanId={cleanId}
              onCleanIdChange={setCleanId}
              onSuccess={refreshAll}
            />
          </div>
        ) : null}

        {chunkSets.length > 0 ? (
          <ul className="mt-4 space-y-1 text-sm text-[var(--muted)]">
            {chunkSets.map((c) => {
              const emptyReason = chunkSetEmptyReason(c.meta);
              return (
                <li key={c.id}>
                  <span
                    className={
                      emptyReason ? "text-[var(--danger,#b42318)]" : undefined
                    }
                  >
                    {artifactLabel(c)}
                  </span>{" "}
                  <Link
                    href={`/projects/${projectId}/artifacts/${c.id}`}
                    className="text-[var(--accent)] underline"
                  >
                    {t("common.view")}
                  </Link>
                </li>
              );
            })}
          </ul>
        ) : null}
      </Section>
    </div>
  );
}

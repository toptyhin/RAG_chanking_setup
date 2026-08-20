"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArtifactContentView,
  RawJsonToggle,
} from "@/components/artifact-content";
import { ArtifactLineageView } from "@/components/artifact-lineage";
import { Button, ErrorBox, Section } from "@/components/ui";
import {
  deleteArtifact,
  getArtifact,
  getArtifactContent,
  getProject,
  listArtifacts,
} from "@/lib/api";
import {
  artifactDisplayName,
  artifactSummary,
  chunkSetEmptyReason,
  formatWhen,
  shortId,
} from "@/lib/format";
import { useI18n } from "@/lib/locale";

export default function ArtifactDetailPage() {
  const { t, bcp47 } = useI18n();
  const router = useRouter();
  const qc = useQueryClient();
  const params = useParams<{ projectId: string; artifactId: string }>();
  const { projectId, artifactId } = params;

  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });

  const artifact = useQuery({
    queryKey: ["artifact", artifactId],
    queryFn: () => getArtifact(artifactId),
  });

  const projectArtifacts = useQuery({
    queryKey: ["artifacts", projectId],
    queryFn: () => listArtifacts(projectId),
    enabled: Boolean(artifact.data && artifact.data.project_id === projectId),
  });

  const content = useQuery({
    queryKey: ["artifact-content", artifactId],
    queryFn: () => getArtifactContent(artifactId),
    enabled: Boolean(artifact.data?.object_key),
    retry: false,
  });

  const wrongProject =
    artifact.data && artifact.data.project_id !== projectId
      ? t("artifactDetail.wrongProject")
      : null;

  const summary = artifact.data
    ? artifactSummary(artifact.data.meta, t)
    : null;
  const emptyReason =
    artifact.data?.type === "chunk_set"
      ? chunkSetEmptyReason(artifact.data.meta)
      : null;

  const remove = useMutation({
    mutationFn: () => deleteArtifact(artifactId, { cascade: true }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["artifacts", projectId] });
      router.push(`/projects/${projectId}/artifacts`);
    },
  });

  function onDelete() {
    if (!artifact.data) return;
    const name = artifactDisplayName(
      artifact.data.type,
      artifact.data.meta,
      artifactId,
    );
    if (!window.confirm(t("artifactDetail.deleteConfirm", { name }))) return;
    remove.mutate();
  }

  return (
    <div>
      <p className="text-sm text-[var(--muted)]">
        <Link href="/projects">{t("common.projects")}</Link> /{" "}
        <Link href={`/projects/${projectId}`}>
          {project.data?.name ?? projectId}
        </Link>{" "}
        /{" "}
        <Link href={`/projects/${projectId}/artifacts`}>
          {t("common.artifacts")}
        </Link>{" "}
        /{" "}
        {artifact.data
          ? artifactDisplayName(
              artifact.data.type,
              artifact.data.meta,
              artifactId,
            )
          : shortId(artifactId)}
      </p>

      <div className="mt-2 mb-1 flex items-center gap-2">
        <button
          type="button"
          onClick={() => router.back()}
          className="inline-flex size-8 shrink-0 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--accent-soft)] hover:text-[var(--fg)]"
          aria-label={t("common.back")}
          title={t("common.back")}
        >
          <svg
            aria-hidden
            viewBox="0 0 16 16"
            className="size-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M10 3 5 8l5 5" />
          </svg>
        </button>
        <h1 className="text-xl font-semibold leading-8">
          {artifact.data
            ? artifactDisplayName(
                artifact.data.type,
                artifact.data.meta,
                artifactId,
              )
            : t("artifactDetail.artifact")}
        </h1>
      </div>
      <p className="font-mono text-xs text-[var(--muted)]">{artifactId}</p>

      {artifact.isLoading ? (
        <p className="mt-4 text-sm text-[var(--muted)]">{t("common.loading")}</p>
      ) : null}
      {artifact.isError ? (
        <ErrorBox message={(artifact.error as Error).message} />
      ) : null}
      {wrongProject ? <ErrorBox message={wrongProject} /> : null}
      {emptyReason ? (
        <ErrorBox
          message={`${t("artifactDetail.emptyChunkSet")}: ${emptyReason}`}
        />
      ) : null}

      {artifact.data && !wrongProject ? (
        <>
          <Section
            title={t("artifactDetail.metadataTitle")}
            description={t("artifactDetail.metadataDescription")}
          >
            <dl className="grid gap-2 sm:grid-cols-2">
              <MetaItem
                label={t("artifactDetail.type")}
                value={artifact.data.type}
              />
              <MetaItem
                label={t("artifactDetail.created")}
                value={formatWhen(artifact.data.created_at, bcp47)}
              />
              <MetaItem
                label={t("artifactDetail.summary")}
                value={summary ?? t("common.emDash")}
              />
              <MetaItem
                label={t("artifactDetail.contentHash")}
                value={artifact.data.content_hash ?? t("common.emDash")}
                mono
              />
              <MetaItem
                label={t("artifactDetail.objectKey")}
                value={artifact.data.object_key ?? t("common.emDash")}
                mono
              />
            </dl>
            {Object.keys(artifact.data.meta).length > 0 ? (
              <div className="mt-4">
                <p className="mb-1 text-xs font-medium text-[var(--muted)]">
                  {t("artifactDetail.meta")}
                </p>
                <pre className="overflow-auto rounded-md border border-[var(--border)] bg-[var(--bg)]/50 p-3 text-xs">
                  {JSON.stringify(artifact.data.meta, null, 2)}
                </pre>
              </div>
            ) : null}
          </Section>

          <Section
            title={t("artifactDetail.lineageTitle")}
            description={t("artifactDetail.lineageDescription")}
          >
            {projectArtifacts.isLoading ? (
              <p className="text-sm text-[var(--muted)]">
                {t("common.loading")}
              </p>
            ) : projectArtifacts.isError ? (
              <ErrorBox message={(projectArtifacts.error as Error).message} />
            ) : (
              <ArtifactLineageView
                projectId={projectId}
                artifact={artifact.data}
                projectArtifacts={projectArtifacts.data ?? []}
              />
            )}
          </Section>

          <Section
            title={t("artifactDetail.contentTitle")}
            description={t("artifactDetail.contentDescription")}
          >
            {!artifact.data.object_key ? (
              <p className="text-sm text-[var(--muted)]">
                {t("artifactDetail.noObject")}
              </p>
            ) : content.isLoading ? (
              <p className="text-sm text-[var(--muted)]">
                {t("artifactDetail.loadingContent")}
              </p>
            ) : content.isError ? (
              <ErrorBox message={(content.error as Error).message} />
            ) : (
              <>
                <ArtifactContentView
                  type={artifact.data.type}
                  content={content.data}
                />
                <div className="mt-6">
                  <RawJsonToggle content={content.data} />
                </div>
              </>
            )}
          </Section>

          <Section
            title={t("artifactDetail.deleteTitle")}
            description={t("artifactDetail.deleteDescription")}
          >
            <Button
              type="button"
              className="bg-[var(--danger,#b42318)] text-white"
              disabled={remove.isPending}
              onClick={onDelete}
            >
              {remove.isPending ? t("common.deleting") : t("common.delete")}
            </Button>
            {remove.isError ? (
              <ErrorBox message={(remove.error as Error).message} />
            ) : null}
          </Section>
        </>
      ) : null}
    </div>
  );
}

function MetaItem({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="rounded-md border border-[var(--border)] px-3 py-2">
      <dt className="text-xs text-[var(--muted)]">{label}</dt>
      <dd
        className={`mt-0.5 break-all text-sm ${mono ? "font-mono text-xs" : ""}`}
      >
        {value}
      </dd>
    </div>
  );
}

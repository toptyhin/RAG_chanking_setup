"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { BackLink } from "@/components/back-link";
import { ImportArtifactsPanel } from "@/components/import-artifacts";
import { ErrorBox, Label, Section, Select } from "@/components/ui";
import { deleteArtifact, getProject, listArtifacts } from "@/lib/api";
import {
  artifactDisplayName,
  artifactSummary,
  artifactTypeLabel,
  formatWhen,
} from "@/lib/format";
import { useI18n } from "@/lib/locale";
import { readReturnTo } from "@/lib/return-to";
import type { Artifact } from "@/lib/types";

const TYPES = [
  "",
  "raw_bundle",
  "clean_corpus",
  "chunk_set",
  "test_set",
  "index_run",
] as const;

export default function ArtifactsListPage() {
  const { t, bcp47 } = useI18n();
  const params = useParams<{ projectId: string }>();
  const projectId = params.projectId;
  const fallbackBack = `/projects/${projectId}`;
  const [backHref, setBackHref] = useState(fallbackBack);
  const qc = useQueryClient();
  const [typeFilter, setTypeFilter] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteNotice, setDeleteNotice] = useState<string | null>(null);

  useEffect(() => {
    setBackHref(readReturnTo(window.location.search, fallbackBack));
  }, [fallbackBack]);

  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });

  const artifacts = useQuery({
    queryKey: ["artifacts", projectId],
    queryFn: () => listArtifacts(projectId),
  });

  const filtered = useMemo(() => {
    const rows = artifacts.data ?? [];
    if (!typeFilter) return rows;
    return rows.filter((a) => a.type === typeFilter);
  }, [artifacts.data, typeFilter]);

  const remove = useMutation({
    mutationFn: (artifact: Artifact) =>
      deleteArtifact(artifact.id, { cascade: true }),
    onSuccess: async (data) => {
      setDeleteError(null);
      setDeleteNotice(t("artifactsPage.deleted", { count: data.deleted.length }));
      await qc.invalidateQueries({ queryKey: ["artifacts", projectId] });
    },
    onError: (err) => {
      setDeleteNotice(null);
      setDeleteError(err instanceof Error ? err.message : String(err));
    },
  });

  function onDelete(a: Artifact) {
    const name = artifactDisplayName(a.type, a.meta, a.id);
    if (!window.confirm(t("artifactsPage.deleteConfirm", { name }))) return;
    remove.mutate(a);
  }

  return (
    <div>
      <p className="text-sm text-[var(--muted)]">
        <Link href="/projects">{t("common.projects")}</Link> /{" "}
        <Link href={`/projects/${projectId}`}>
          {project.data?.name ?? projectId}
        </Link>{" "}
        / {t("common.artifacts")}
      </p>
      <div className="mb-2 flex items-center gap-2">
        <BackLink href={backHref} label={t("common.back")} />
        <h1 className="text-xl font-semibold leading-8">{t("artifactsPage.title")}</h1>
      </div>
      <p className="mb-6 max-w-2xl text-sm text-[var(--muted)]">
        {t("artifactsPage.intro")}
      </p>

      <Section
        title={t("artifactsPage.importTitle")}
        description={t("artifactsPage.importDescription")}
      >
        <ImportArtifactsPanel projectId={projectId} />
      </Section>

      <Section
        title={t("artifactsPage.libraryTitle")}
        description={t("artifactsPage.libraryDescription")}
      >
        <div className="mb-4 max-w-xs">
          <Label>{t("artifactsPage.typeFilter")}</Label>
          <Select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            {TYPES.map((type) => (
              <option key={type || "all"} value={type}>
                {type ? artifactTypeLabel(type, t) : t("common.all")}
              </option>
            ))}
          </Select>
        </div>

        {artifacts.isLoading ? (
          <p className="text-sm text-[var(--muted)]">{t("common.loading")}</p>
        ) : null}
        {artifacts.isError ? (
          <ErrorBox message={(artifacts.error as Error).message} />
        ) : null}
        {deleteError ? <ErrorBox message={deleteError} /> : null}
        {deleteNotice ? (
          <p className="mb-3 text-sm text-[var(--muted)]">{deleteNotice}</p>
        ) : null}

        {filtered.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">
            {t("artifactsPage.empty")}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                  <th className="py-2 pr-3 font-medium">
                    {t("artifactsPage.tableType")}
                  </th>
                  <th className="py-2 pr-3 font-medium">
                    {t("artifactsPage.tableId")}
                  </th>
                  <th className="py-2 pr-3 font-medium">
                    {t("artifactsPage.tableSummary")}
                  </th>
                  <th className="py-2 pr-3 font-medium">
                    {t("artifactsPage.tableCreated")}
                  </th>
                  <th className="py-2 font-medium" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((a) => (
                  <tr key={a.id} className="border-b border-[var(--border)]">
                    <td className="py-2 pr-3">
                      {artifactTypeLabel(a.type, t)}
                      <code className="ml-2 text-xs text-[var(--muted)]">{a.type}</code>
                    </td>
                    <td className="py-2 pr-3">
                      <code className="text-xs">
                        {artifactDisplayName(a.type, a.meta, a.id)}
                      </code>
                    </td>
                    <td className="py-2 pr-3 text-[var(--muted)]">
                      {artifactSummary(a.meta, t) ?? t("common.emDash")}
                    </td>
                    <td className="py-2 pr-3 text-xs text-[var(--muted)]">
                      {formatWhen(a.created_at, bcp47)}
                    </td>
                    <td className="py-2 text-right">
                      <div className="flex items-center justify-end gap-3">
                        <Link
                          href={`/projects/${projectId}/artifacts/${a.id}`}
                          className="text-[var(--accent)] underline"
                        >
                          {t("common.view")}
                        </Link>
                        <button
                          type="button"
                          className="text-[var(--danger,#b42318)] underline disabled:opacity-50"
                          disabled={remove.isPending}
                          onClick={() => onDelete(a)}
                        >
                          {remove.isPending && remove.variables?.id === a.id
                            ? t("common.deleting")
                            : t("common.delete")}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  );
}

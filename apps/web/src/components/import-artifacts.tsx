"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  importArtifactsFromProject,
  listArtifacts,
  listProjects,
} from "@/lib/api";
import { artifactDisplayName, artifactSummary } from "@/lib/format";
import { useI18n } from "@/lib/locale";
import { Button, ErrorBox, Label, Select } from "@/components/ui";

const IMPORTABLE = new Set([
  "raw_bundle",
  "clean_corpus",
  "chunk_set",
  "test_set",
]);

type Props = {
  projectId: string;
};

export function ImportArtifactsPanel({ projectId }: Props) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [sourceProjectId, setSourceProjectId] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [includeParents, setIncludeParents] = useState(true);

  const projects = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  const sourceOptions = useMemo(
    () => (projects.data ?? []).filter((p) => p.id !== projectId),
    [projects.data, projectId],
  );

  const sourceArtifacts = useQuery({
    queryKey: ["artifacts", sourceProjectId],
    queryFn: () => listArtifacts(sourceProjectId),
    enabled: Boolean(sourceProjectId),
  });

  const selectedSet = useMemo(() => new Set(selected), [selected]);

  const importable = useMemo(
    () =>
      (sourceArtifacts.data ?? []).filter((a) => IMPORTABLE.has(a.type)),
    [sourceArtifacts.data],
  );

  const importMut = useMutation({
    mutationFn: () =>
      importArtifactsFromProject(projectId, {
        source_project_id: sourceProjectId,
        artifact_ids: selected,
        include_parents: includeParents,
      }),
    onSuccess: async () => {
      setSelected([]);
      await qc.invalidateQueries({ queryKey: ["artifacts", projectId] });
    },
  });

  function toggle(id: string) {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  function selectAll() {
    setSelected(importable.map((a) => a.id));
  }

  if (sourceOptions.length === 0) {
    return (
      <p className="text-sm text-[var(--muted)]">
        {t("importArtifacts.noOtherProjects")}
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-[var(--muted)]">
        {t("importArtifacts.hint")}
      </p>
      <div className="max-w-md">
        <Label>{t("importArtifacts.sourceProject")}</Label>
        <Select
          value={sourceProjectId}
          onChange={(e) => {
            setSourceProjectId(e.target.value);
            setSelected([]);
          }}
        >
          <option value="">{t("importArtifacts.chooseProject")}</option>
          {sourceOptions.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </Select>
      </div>

      {sourceProjectId ? (
        <>
          {sourceArtifacts.isLoading ? (
            <p className="text-sm text-[var(--muted)]">{t("common.loading")}</p>
          ) : null}
          {sourceArtifacts.isError ? (
            <ErrorBox message={(sourceArtifacts.error as Error).message} />
          ) : null}
          {importable.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">
              {t("importArtifacts.emptySource")}
            </p>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  className="text-xs text-[var(--accent)] underline"
                  onClick={selectAll}
                >
                  {t("importArtifacts.selectAll")}
                </button>
                <label className="flex items-center gap-2 text-xs text-[var(--muted)]">
                  <input
                    type="checkbox"
                    checked={includeParents}
                    onChange={(e) => setIncludeParents(e.target.checked)}
                  />
                  {t("importArtifacts.includeParents")}
                </label>
              </div>
              <div className="max-h-48 overflow-y-auto rounded-md border border-[var(--border)] bg-[var(--bg)]/40 p-2">
                {importable.map((a) => {
                  const summary = artifactSummary(a.meta, t);
                  return (
                    <label
                      key={a.id}
                      className="flex cursor-pointer items-start gap-2 rounded px-2 py-1.5 text-sm hover:bg-[var(--accent-soft)]"
                    >
                      <input
                        type="checkbox"
                        className="mt-1"
                        checked={selectedSet.has(a.id)}
                        onChange={() => toggle(a.id)}
                      />
                      <span>
                        <code className="text-xs font-medium">
                          {artifactDisplayName(a.type, a.meta, a.id)}
                        </code>
                        {summary ? (
                          <span className="block text-xs text-[var(--muted)]">
                            {summary}
                          </span>
                        ) : null}
                      </span>
                    </label>
                  );
                })}
              </div>
              <Button
                type="button"
                disabled={importMut.isPending || selected.length === 0}
                onClick={() => importMut.mutate()}
              >
                {importMut.isPending
                  ? t("importArtifacts.importing")
                  : t("importArtifacts.importSelected", {
                      count: selected.length,
                    })}
              </Button>
            </>
          )}
        </>
      ) : null}

      {importMut.isError ? (
        <ErrorBox message={(importMut.error as Error).message} />
      ) : null}
      {importMut.isSuccess ? (
        <p className="text-sm text-[var(--muted)]">
          {t("importArtifacts.success", {
            count: importMut.data.artifacts.length,
          })}
        </p>
      ) : null}
    </div>
  );
}

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { createProject, listProjects } from "@/lib/api";
import { useI18n } from "@/lib/locale";
import { Button, ErrorBox, Input, Label, Section } from "@/components/ui";

export default function ProjectsPage() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const projects = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  const create = useMutation({
    mutationFn: createProject,
    onSuccess: async (project) => {
      setName("");
      setDescription("");
      await qc.invalidateQueries({ queryKey: ["projects"] });
      router.push(`/projects/${project.id}`);
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    create.mutate({
      name: name.trim(),
      description: description.trim() || null,
    });
  }

  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold">{t("projectsPage.title")}</h1>

      <Section
        title={t("projectsPage.createTitle")}
        description={t("projectsPage.createDescription")}
      >
        <form onSubmit={onSubmit} className="grid gap-3 sm:grid-cols-2">
          <div className="sm:col-span-1">
            <Label>{t("projectsPage.name")}</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("projectsPage.namePlaceholder")}
              required
            />
          </div>
          <div className="sm:col-span-1">
            <Label>{t("projectsPage.description")}</Label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("projectsPage.descriptionPlaceholder")}
            />
          </div>
          <div className="sm:col-span-2">
            <Button type="submit" disabled={create.isPending || !name.trim()}>
              {create.isPending
                ? t("projectsPage.creating")
                : t("projectsPage.create")}
            </Button>
            {create.isError ? (
              <ErrorBox message={(create.error as Error).message} />
            ) : null}
          </div>
        </form>
      </Section>

      <Section title={t("projectsPage.allProjects")}>
        {projects.isLoading ? (
          <p className="text-sm text-[var(--muted)]">{t("common.loading")}</p>
        ) : null}
        {projects.isError ? (
          <ErrorBox message={(projects.error as Error).message} />
        ) : null}
        {projects.data?.length === 0 ? (
          <div className="rounded-lg border border-dashed border-[var(--border)] bg-[var(--bg)]/35 p-5">
            <p className="font-medium">{t("projectsPage.emptyTitle")}</p>
            <p className="mt-1 max-w-xl text-sm text-[var(--muted)]">
              {t("projectsPage.empty")}
            </p>
            <button
              type="button"
              className="mt-3 text-sm font-medium text-[var(--accent)] underline"
              onClick={() => document.querySelector<HTMLInputElement>('input[required]')?.focus()}
            >
              {t("projectsPage.emptyCta")}
            </button>
          </div>
        ) : null}
        <ul className="divide-y divide-[var(--border)]">
          {projects.data?.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-3 py-3">
              <div>
                <Link
                  href={`/projects/${p.id}`}
                  className="font-medium text-[var(--accent)]"
                >
                  {p.name}
                </Link>
                {p.description ? (
                  <p className="text-sm text-[var(--muted)]">{p.description}</p>
                ) : null}
              </div>
              <code className="text-xs text-[var(--muted)]">{p.id}</code>
            </li>
          ))}
        </ul>
      </Section>
    </div>
  );
}

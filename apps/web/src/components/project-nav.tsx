"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useI18n } from "@/lib/locale";
import { withReturnTo } from "@/lib/return-to";

export type ProjectStage = "overview" | "data" | "test" | "labs" | "results";

export function ProjectNav({
  projectId,
  value,
}: {
  projectId: string;
  value: ProjectStage;
}) {
  const { t } = useI18n();
  const pathname = usePathname();
  const stages: Array<{
    id: ProjectStage;
    label: string;
    description: string;
    href: string;
  }> = [
    { id: "overview", label: t("projectNav.overview"), description: t("projectNav.overviewHint"), href: `/projects/${projectId}` },
    { id: "data", label: t("projectNav.data"), description: t("projectNav.dataHint"), href: `/projects/${projectId}/data` },
    { id: "test", label: t("projectNav.testSet"), description: t("projectNav.testSetHint"), href: `/projects/${projectId}/test-set` },
    { id: "labs", label: t("projectNav.labs"), description: t("projectNav.labsHint"), href: `/projects/${projectId}/labs` },
    { id: "results", label: t("projectNav.results"), description: t("projectNav.resultsHint"), href: `/projects/${projectId}/results` },
  ];

  return (
    <nav className="mb-6" aria-label={t("projectNav.flow")}>
      <ol className="grid gap-2 md:grid-cols-5">
        {stages.map((stage, index) => {
          const active = stage.id === value;
          return (
            <li key={stage.id}>
              <Link
                href={stage.href}
                aria-current={active ? "page" : undefined}
                className={`block h-full rounded-lg border px-3 py-2 no-underline ${
                  active
                    ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--fg)]"
                    : "border-[var(--border)] text-[var(--muted)] hover:border-[var(--accent)]/50 hover:text-[var(--fg)]"
                }`}
              >
                <span className="text-xs font-semibold text-[var(--accent)]">
                  {index + 1}
                </span>
                <span className="ml-2 text-sm font-medium">{stage.label}</span>
                <span className="mt-1 block text-xs leading-snug">
                  {stage.description}
                </span>
              </Link>
            </li>
          );
        })}
      </ol>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--muted)]">
        <Link
          href={withReturnTo("/settings/connections", pathname)}
          className="hover:text-[var(--fg)]"
        >
          {t("projectNav.connections")}
        </Link>
        <Link
          href={withReturnTo(`/projects/${projectId}/artifacts`, pathname)}
          className="hover:text-[var(--fg)]"
        >
          {t("projectNav.artifacts")}
        </Link>
      </div>
    </nav>
  );
}

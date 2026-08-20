"use client";

import Link from "next/link";
import { useI18n } from "@/lib/locale";

export default function ProjectNotFound() {
  const { t } = useI18n();
  return (
    <div className="max-w-xl rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
      <h1 className="text-xl font-semibold">{t("routeErrors.notFoundTitle")}</h1>
      <p className="mt-2 text-sm text-[var(--muted)]">
        {t("routeErrors.notFoundDescription")}
      </p>
      <Link href="/projects" className="mt-4 inline-block text-sm font-medium text-[var(--accent)] underline">
        {t("common.projects")}
      </Link>
    </div>
  );
}

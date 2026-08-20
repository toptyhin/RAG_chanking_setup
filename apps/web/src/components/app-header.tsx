"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LocaleToggle } from "@/components/locale-toggle";
import { ThemeToggle } from "@/components/theme-toggle";
import { useI18n } from "@/lib/locale";
import { withReturnTo } from "@/lib/return-to";

export function AppHeader() {
  const { t } = useI18n();
  const pathname = usePathname();
  const connectionsHref =
    pathname === "/settings/connections"
      ? "/settings/connections"
      : withReturnTo("/settings/connections", pathname);

  return (
    <header className="mb-8 flex flex-col gap-4 border-b border-[var(--border)] pb-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <Link href="/projects" className="text-2xl font-semibold tracking-tight">
          rageval
        </Link>
        <p className="mt-1 text-sm text-[var(--muted)]">{t("layout.tagline")}</p>
      </div>
      <nav
        aria-label={t("layout.mainNav")}
        className="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm text-[var(--muted)]"
      >
        <Link href="/projects">{t("layout.projectsNav")}</Link>
        <Link href={connectionsHref}>{t("layout.connectionsNav")}</Link>
        <Link href="/learn">{t("layout.learnNav")}</Link>
        <div className="flex items-center gap-1.5">
          <LocaleToggle />
          <ThemeToggle />
        </div>
      </nav>
    </header>
  );
}

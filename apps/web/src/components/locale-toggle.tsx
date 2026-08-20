"use client";

import { LOCALE_LABELS, type Locale } from "@/i18n";
import { useI18n } from "@/lib/locale";

export function LocaleToggle() {
  const { locale, cycle, t } = useI18n();
  const label = LOCALE_LABELS[locale];
  const next: Locale = locale === "en" ? "ru" : "en";

  return (
    <button
      type="button"
      onClick={cycle}
      className="inline-flex h-8 min-w-8 items-center justify-center rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 text-xs font-semibold tracking-wide text-[var(--muted)] hover:text-[var(--fg)]"
      title={t("locale.label")}
      aria-label={t("locale.aria", { label: LOCALE_LABELS[next] })}
    >
      {label}
    </button>
  );
}

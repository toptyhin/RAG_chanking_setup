"use client";

import { evidenceLevelOf, type EvidenceLevel } from "@/lib/evidence-level";
import { useI18n } from "@/lib/locale";
import type { TranslationKey } from "@/i18n";

const LEVEL_STYLES: Record<
  Exclude<EvidenceLevel, "other">,
  { label: string; shortKey: TranslationKey; className: string }
> = {
  l1: {
    label: "L1",
    shortKey: "projectPage.difficultyShortL1",
    className:
      "bg-emerald-500/15 text-emerald-800 ring-emerald-600/30 dark:text-emerald-300",
  },
  l2: {
    label: "L2",
    shortKey: "projectPage.difficultyShortL2",
    className:
      "bg-sky-500/15 text-sky-800 ring-sky-600/30 dark:text-sky-300",
  },
  l3: {
    label: "L3",
    shortKey: "projectPage.difficultyShortL3",
    className:
      "bg-amber-500/15 text-amber-900 ring-amber-600/35 dark:text-amber-300",
  },
  l4: {
    label: "L4",
    shortKey: "projectPage.difficultyShortL4",
    className:
      "bg-rose-500/15 text-rose-900 ring-rose-600/30 dark:text-rose-300",
  },
};

export function DifficultyBadge({
  level,
  queryType,
  showShort = false,
  className = "",
}: {
  level?: string | null;
  queryType?: string | null;
  /** Show short label after L1–L4 (fact / multi-hop / …). */
  showShort?: boolean;
  className?: string;
}) {
  const { t } = useI18n();
  const key = evidenceLevelOf(level, queryType);
  if (key === "other") {
    const raw = (level || queryType || "").trim();
    if (!raw) return null;
    return (
      <span
        className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)] ring-1 ring-[var(--border)] ${className}`}
      >
        {raw}
      </span>
    );
  }
  const style = LEVEL_STYLES[key];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold tracking-wide ring-1 ${style.className} ${className}`}
      title={`${style.label} — ${t(style.shortKey)}`}
    >
      {style.label}
      {showShort ? (
        <span className="font-normal opacity-80">{t(style.shortKey)}</span>
      ) : null}
    </span>
  );
}

export function DifficultyLegendRow({
  level,
  description,
}: {
  level: "l1" | "l2" | "l3" | "l4";
  description: string;
}) {
  return (
    <li className="flex items-start gap-2">
      <DifficultyBadge level={level} className="mt-0.5 shrink-0" />
      <span>{description}</span>
    </li>
  );
}

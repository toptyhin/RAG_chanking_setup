/** Match DifficultyBadge palette (solid fills for chart legend). */
export const LEVEL_FILL: Record<string, string> = {
  l1: "#059669",
  l2: "#0284c7",
  l3: "#d97706",
  l4: "#e11d48",
};

const OTHER_FILLS = ["#7c3aed", "#0891b2", "#64748b", "#a855f7"];

export function fillForDifficultyType(type: string, index: number): string {
  const key = type.trim().toLowerCase();
  if (LEVEL_FILL[key]) return LEVEL_FILL[key]!;
  return OTHER_FILLS[index % OTHER_FILLS.length]!;
}

export function formatDifficultyDelta(delta: number | null): string {
  if (delta == null) return "—";
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(3)}`;
}

export const difficultyTooltipStyle = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontSize: 12,
} as const;

"use client";

import dynamic from "next/dynamic";
import { DifficultyBreakdownControls } from "@/components/difficulty-breakdown-controls";
import { DifficultyBreakdownMatrix } from "@/components/difficulty-breakdown-matrix";
import { useDifficultyBreakdown } from "@/components/use-difficulty-breakdown";
import type { MetricsRow } from "@/lib/types";

const DifficultyBreakdownChart = dynamic(
  () =>
    import("@/components/difficulty-breakdown-chart").then(
      (m) => m.DifficultyBreakdownChart,
    ),
  { ssr: false },
);

export function DifficultyBreakdown({ rows }: { rows: MetricsRow[] }) {
  const breakdown = useDifficultyBreakdown(rows);

  if (breakdown.withBreakdown.length === 0) return null;

  return (
    <div className="space-y-6">
      <DifficultyBreakdownControls {...breakdown} />
      <DifficultyBreakdownChart {...breakdown} />
      <DifficultyBreakdownMatrix {...breakdown} />
    </div>
  );
}

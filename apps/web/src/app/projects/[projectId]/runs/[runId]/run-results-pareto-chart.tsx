"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/lib/locale";

type ParetoChartProps = {
  chartData: Array<{
    name: string;
    recall: number;
    latency: number;
    size: number;
  }>;
};

export function RunResultsParetoChart({ chartData }: ParetoChartProps) {
  const { t } = useI18n();
  const [recharts, setRecharts] = useState<Awaited<
    typeof import("recharts")
  > | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const mod = await import("recharts");
        if (!cancelled) setRecharts(mod);
      } catch {
        // Keep placeholder if recharts fails to load.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!recharts) {
    return <div className="h-72 w-full" aria-hidden />;
  }

  const {
    CartesianGrid,
    Legend,
    ResponsiveContainer,
    Scatter,
    ScatterChart,
    Tooltip,
    XAxis,
    YAxis,
    ZAxis,
  } = recharts;

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            type="number"
            dataKey="latency"
            name="latency_p95_ms"
            unit=" ms"
          />
          <YAxis type="number" dataKey="recall" name="recall" domain={[0, 1]} />
          <ZAxis type="number" dataKey="size" range={[60, 200]} name="index_mb" />
          <Tooltip cursor={{ strokeDasharray: "3 3" }} />
          <Legend />
          <Scatter
            name={t("runPage.paretoLegend")}
            data={chartData}
            fill="var(--chart)"
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

import { describe, expect, it } from "vitest";
import {
  buildDifficultyCurve,
  buildDifficultyGroupedByConfig,
  buildHeatmapMatrix,
  deltaVsOverall,
  flattenQueryTypeBreakdown,
  formatDifficultyLabel,
  heatmapCellStyle,
  listBreakdownMetrics,
  orderQueryTypes,
} from "./query-type";

describe("orderQueryTypes", () => {
  it("puts L1–L4 before other labels", () => {
    expect(orderQueryTypes(["factoid", "l3", "l1", "multi-hop", "l2"])).toEqual(
      ["l1", "l2", "l3", "factoid", "multi-hop"],
    );
  });
});

describe("formatDifficultyLabel", () => {
  it("uppercases L1–L4", () => {
    expect(formatDifficultyLabel("l1")).toBe("L1");
    expect(formatDifficultyLabel("L3")).toBe("L3");
    expect(formatDifficultyLabel("factoid")).toBe("factoid");
  });
});

describe("flattenQueryTypeBreakdown", () => {
  it("splits type.metric keys", () => {
    const rows = flattenQueryTypeBreakdown({
      by_query_type: {
        "l1.recall@5": 0.9,
        "l3.ndcg@5": 0.4,
      },
    });
    expect(rows).toEqual([
      { type: "l1", metric: "recall@5", value: 0.9 },
      { type: "l3", metric: "ndcg@5", value: 0.4 },
    ]);
  });
});

describe("listBreakdownMetrics", () => {
  it("prefers recall@5", () => {
    const metrics = listBreakdownMetrics([
      { type: "l1", metric: "ndcg@5", value: 0.5 },
      { type: "l1", metric: "recall@5", value: 0.8 },
      { type: "l1", metric: "recall@1", value: 0.6 },
    ]);
    expect(metrics[0]).toBe("recall@5");
    expect(metrics).toContain("ndcg@5");
  });
});

describe("buildDifficultyCurve", () => {
  it("builds series columns per config with L1 labels", () => {
    const { data, series } = buildDifficultyCurve(
      [
        {
          pointIndex: 0,
          metrics: {
            by_query_type: { "l1.recall@5": 1, "l2.recall@5": 0.8 },
          },
        },
        {
          pointIndex: 1,
          metrics: {
            by_query_type: { "l1.recall@5": 0.7, "l3.recall@5": 0.2 },
          },
        },
      ],
      "recall@5",
    );
    expect(series.map((s) => s.key)).toEqual(["p0", "p1"]);
    expect(data.map((d) => d.label)).toEqual(["L1", "L2", "L3"]);
    expect(data[0]).toMatchObject({ type: "l1", p0: 1, p1: 0.7 });
    expect(data[1]).toMatchObject({ type: "l2", p0: 0.8, p1: null });
  });
});

describe("buildDifficultyGroupedByConfig", () => {
  it("uses L-level columns for legend", () => {
    const { data, types } = buildDifficultyGroupedByConfig(
      [
        {
          pointIndex: 0,
          metrics: { by_query_type: { "l1.recall@5": 1, "l4.recall@5": 0.2 } },
        },
        {
          pointIndex: 2,
          metrics: { by_query_type: { "l1.recall@5": 0.5 } },
        },
      ],
      "recall@5",
    );
    expect(types).toEqual(["l1", "l4"]);
    expect(data[0]).toMatchObject({
      configLabel: "#0",
      l1: 1,
      l4: 0.2,
    });
    expect(data[1]).toMatchObject({ configLabel: "#2", l1: 0.5, l4: null });
  });
});

describe("buildHeatmapMatrix", () => {
  it("includes delta vs overall", () => {
    const matrix = buildHeatmapMatrix({
      "recall@5": 0.7,
      by_query_type: {
        "l1.recall@5": 0.9,
        "l4.recall@5": 0.4,
      },
    });
    expect(matrix.types).toEqual(["l1", "l4"]);
    const l4 = matrix.cells.find(
      (c) => c.type === "l4" && c.metric === "recall@5",
    );
    expect(l4?.value).toBe(0.4);
    expect(l4?.delta).toBeCloseTo(-0.3);
  });
});

describe("deltaVsOverall / heatmapCellStyle", () => {
  it("computes delta", () => {
    expect(deltaVsOverall(0.4, 0.7)).toBeCloseTo(-0.3);
    expect(deltaVsOverall(null, 0.7)).toBeNull();
  });

  it("returns transparent for null", () => {
    expect(heatmapCellStyle(null).backgroundColor).toBe("transparent");
  });
});

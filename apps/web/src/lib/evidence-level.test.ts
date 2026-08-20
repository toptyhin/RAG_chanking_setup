import { describe, expect, it } from "vitest";
import {
  evidenceLevelOf,
  evidenceWarnings,
  minEvidenceChunks,
  needsEvidenceReview,
  validateEvidenceDraft,
} from "./evidence-level";

describe("evidenceLevelOf", () => {
  it("normalizes L1–L4", () => {
    expect(evidenceLevelOf("L3")).toBe("l3");
    expect(evidenceLevelOf(undefined, "l4")).toBe("l4");
    expect(evidenceLevelOf("Multi hop")).toBe("other");
  });
});

describe("validateEvidenceDraft", () => {
  it("requires two premises for L3", () => {
    const issues = validateEvidenceDraft([
      { text: "q", relevant: ["a"], level: "L3" },
    ]);
    expect(issues).toEqual([{ questionIndex: 0, code: "need_two" }]);
  });

  it("allows one chunk for L4 (warning only)", () => {
    expect(
      validateEvidenceDraft([{ text: "q", relevant: ["a"], level: "L4" }]),
    ).toEqual([]);
    expect(
      evidenceWarnings([{ text: "q", relevant: ["a"], level: "L4" }]),
    ).toEqual([{ questionIndex: 0, code: "l4_single" }]);
  });

  it("reports missing chunks", () => {
    expect(
      validateEvidenceDraft([{ text: "q", relevant: [], level: "L1" }]),
    ).toEqual([{ questionIndex: 0, code: "need_chunks" }]);
  });
});

describe("needsEvidenceReview", () => {
  it("is true for L3/L4 only", () => {
    expect(needsEvidenceReview("l3")).toBe(true);
    expect(needsEvidenceReview("l4")).toBe(true);
    expect(needsEvidenceReview("l1")).toBe(false);
    expect(minEvidenceChunks("l3")).toBe(2);
    expect(minEvidenceChunks("l4")).toBe(1);
  });
});

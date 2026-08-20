import { describe, expect, it } from "vitest";
import { estimateTokens, sizeFromText } from "./token-estimate";

describe("estimateTokens", () => {
  it("matches ASCII÷4 heuristic", () => {
    expect(estimateTokens("")).toBe(0);
    expect(estimateTokens("abcd")).toBe(1);
    expect(estimateTokens("a".repeat(8))).toBe(2);
  });

  it("treats non-ASCII denser than ASCII", () => {
    expect(estimateTokens("я".repeat(100))).toBe(50);
    expect(estimateTokens("abcdяяяя")).toBe(3);
  });
});

describe("sizeFromText", () => {
  it("returns chars and tokens", () => {
    expect(sizeFromText("hello")).toEqual({ chars: 5, tokens: 2 });
  });
});

import { describe, expect, it } from "vitest";
import {
  chunkSizeFromMeta,
  isEmbeddingDimBelowChunkSize,
  resolveEmbeddingDimensionForModel,
} from "./chunk-embedding-fit";

describe("isEmbeddingDimBelowChunkSize", () => {
  it("warns when dimension is smaller than chunk size", () => {
    expect(isEmbeddingDimBelowChunkSize(384, 512)).toBe(true);
  });

  it("does not warn when dimension is equal or larger", () => {
    expect(isEmbeddingDimBelowChunkSize(768, 512)).toBe(false);
    expect(isEmbeddingDimBelowChunkSize(512, 512)).toBe(false);
  });

  it("does not warn on missing values", () => {
    expect(isEmbeddingDimBelowChunkSize(null, 512)).toBe(false);
    expect(isEmbeddingDimBelowChunkSize(384, null)).toBe(false);
  });
});

describe("chunkSizeFromMeta", () => {
  it("prefers measured length_chars.max_chars over configured size", () => {
    expect(
      chunkSizeFromMeta({
        size: 512,
        length_chars: { max_chars: 1800, min_chars: 40 },
      }),
    ).toBe(1800);
  });

  it("reads size / chunk_size / nested options", () => {
    expect(chunkSizeFromMeta({ size: 512 })).toBe(512);
    expect(chunkSizeFromMeta({ chunk_size: 256 })).toBe(256);
    expect(chunkSizeFromMeta({ options: { max_tokens: 400 } })).toBe(400);
  });
});

describe("resolveEmbeddingDimensionForModel", () => {
  it("uses loaded dim for the selected model, not stale current", () => {
    expect(
      resolveEmbeddingDimensionForModel(
        "ai-forever/ru-en-RoSBERTa",
        [
          { model_id: "sentence-transformers/all-MiniLM-L6-v2", dimension: 384 },
          { model_id: "ai-forever/ru-en-RoSBERTa", dimension: 1024 },
        ],
        {
          model_id: "sentence-transformers/all-MiniLM-L6-v2",
          dimension: 384,
        },
      ),
    ).toBe(1024);
  });
});

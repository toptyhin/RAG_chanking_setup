import type { RemoteModelInfo } from "@/lib/types";

export type RemoteModelPurpose = "text" | "embeddings" | "rerank";

/** Embedding dim label: single native, or MRL sizes when several are known. */
export function formatEmbeddingDims(
  item: Pick<RemoteModelInfo, "dimension" | "dimensions">,
): string | null {
  const mrl = (item.dimensions ?? []).filter((n) => n > 0);
  if (mrl.length > 1) {
    return mrl.join("/");
  }
  if (mrl.length === 1) return String(mrl[0]);
  if (item.dimension != null && item.dimension > 0) {
    return String(item.dimension);
  }
  return null;
}

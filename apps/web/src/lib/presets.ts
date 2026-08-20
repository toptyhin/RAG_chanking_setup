export type RunPresetId =
  | "quick"
  | "topk"
  | "dense_vs_hybrid"
  | "custom_topk";

export type RunPreset = {
  id: Exclude<RunPresetId, "custom_topk">;
  fixed: Record<string, unknown>;
  swept: Record<string, unknown[]>;
};

/** Values accepted by backend `parse_quantization_axis`, plus UI compare mode. */
export type QuantizationChoice =
  | "none"
  | "binary"
  | "binary+rescore"
  | "scalar"
  | "scalar+rescore"
  | "compare";

export const QUANTIZATION_COMPARE_VALUES = [
  "none",
  "binary+rescore",
] as const;

export const RUN_PRESETS: RunPreset[] = [
  {
    id: "quick",
    fixed: { "retrieval.mode": "dense", "retrieval.top_k": 5 },
    swept: {},
  },
  {
    id: "topk",
    fixed: { "retrieval.mode": "dense" },
    swept: { "retrieval.top_k": [1, 5, 10] },
  },
  {
    id: "dense_vs_hybrid",
    fixed: { "retrieval.top_k": 5 },
    swept: { "retrieval.mode": ["dense", "hybrid"] },
  },
];

export function applyQuantizationChoice(
  fixed: Record<string, unknown>,
  swept: Record<string, unknown[]>,
  choice: QuantizationChoice,
): { fixed: Record<string, unknown>; swept: Record<string, unknown[]> } {
  const nextFixed = { ...fixed };
  const nextSwept = { ...swept };
  delete nextFixed.quantization;
  delete nextFixed["index.quantization"];
  delete nextSwept.quantization;
  delete nextSwept["index.quantization"];

  if (choice === "compare") {
    nextSwept.quantization = [...QUANTIZATION_COMPARE_VALUES];
  } else if (choice !== "none") {
    nextFixed.quantization = choice;
  }
  return { fixed: nextFixed, swept: nextSwept };
}

export type ModelPickerKind = "embedding" | "rerank";

export type ModelPickerProps = {
  kind: ModelPickerKind;
  value: string;
  onChange: (modelId: string) => void;
  disabled?: boolean;
};

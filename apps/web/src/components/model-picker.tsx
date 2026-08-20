"use client";

import { ModelPickerView } from "@/components/model-picker-view";
import type { ModelPickerProps } from "@/components/model-picker-types";
import { useModelPicker } from "@/components/use-model-picker";

export type { ModelPickerKind } from "@/components/model-picker-types";

export function ModelPicker({ kind, value, onChange, disabled }: ModelPickerProps) {
  const picker = useModelPicker({ kind, value, onChange });
  return <ModelPickerView picker={picker} disabled={disabled} />;
}

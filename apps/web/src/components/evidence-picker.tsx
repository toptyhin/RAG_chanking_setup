"use client";

import { EvidencePickerView } from "@/components/evidence-picker-view";
import type { EvidencePickerProps } from "@/components/evidence-picker-types";
import { useEvidencePicker } from "@/components/use-evidence-picker";

export function EvidencePicker(props: EvidencePickerProps) {
  const picker = useEvidencePicker(props);
  return <EvidencePickerView picker={picker} />;
}

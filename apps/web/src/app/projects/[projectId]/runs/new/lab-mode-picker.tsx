import { useI18n } from "@/lib/locale";
import type { LabMode } from "./new-run-utils";

type LabModePickerProps = {
  labMode: LabMode;
  onLabModeChange: (mode: LabMode) => void;
};

export function LabModePicker({ labMode, onLabModeChange }: LabModePickerProps) {
  const { t } = useI18n();

  return (
    <div className="mb-6 grid gap-3 sm:grid-cols-3">
      {(["prep", "chunk", "retrieval"] as const).map((mode) => (
        <button
          key={mode}
          type="button"
          onClick={() => onLabModeChange(mode)}
          className={`rounded-lg border p-3 text-left ${
            labMode === mode
              ? "border-[var(--accent)] bg-[var(--accent-soft)]"
              : "border-[var(--border)]"
          }`}
        >
          <p className="text-sm font-semibold">
            {t(
              mode === "prep"
                ? "newRunPage.prepLab"
                : mode === "chunk"
                  ? "newRunPage.chunkLab"
                  : "newRunPage.retrievalLab",
            )}
          </p>
          <p className="mt-1 text-xs text-[var(--muted)]">
            {t(
              mode === "prep"
                ? "newRunPage.prepLabDescription"
                : mode === "chunk"
                  ? "newRunPage.chunkLabDescription"
                  : "newRunPage.retrievalLabDescription",
            )}
          </p>
        </button>
      ))}
    </div>
  );
}

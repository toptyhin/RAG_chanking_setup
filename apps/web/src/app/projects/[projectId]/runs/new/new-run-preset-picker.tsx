import { Input, Label } from "@/components/ui";
import { useI18n } from "@/lib/locale";
import { RUN_PRESETS, type RunPresetId } from "@/lib/presets";
import { presetDescription, presetTitle } from "./new-run-utils";

type NewRunPresetPickerProps = {
  presetId: RunPresetId;
  onPresetIdChange: (id: RunPresetId) => void;
  customTopK: string;
  onCustomTopKChange: (value: string) => void;
};

export function NewRunPresetPicker({
  presetId,
  onPresetIdChange,
  customTopK,
  onCustomTopKChange,
}: NewRunPresetPickerProps) {
  const { t } = useI18n();

  return (
    <div>
      <Label>{t("newRunPage.goalFirst")}</Label>
      <p className="mb-2 text-xs text-[var(--muted)]">{t("newRunPage.goalFirstDescription")}</p>
      <div className="grid gap-2">
        {RUN_PRESETS.map((preset) => (
          <label
            key={preset.id}
            className={`flex cursor-pointer gap-3 rounded-md border px-3 py-3 ${
              presetId === preset.id
                ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                : "border-[var(--border)]"
            }`}
          >
            <input
              type="radio"
              name="preset"
              className="mt-1"
              checked={presetId === preset.id}
              onChange={() => onPresetIdChange(preset.id)}
            />
            <span>
              <span className="block text-sm font-medium">{presetTitle(preset.id, t)}</span>
              <span className="mt-0.5 block text-xs text-[var(--muted)]">
                {presetDescription(preset.id, t)}
              </span>
            </span>
          </label>
        ))}
        <label
          className={`flex cursor-pointer gap-3 rounded-md border px-3 py-3 ${
            presetId === "custom_topk"
              ? "border-[var(--accent)] bg-[var(--accent-soft)]"
              : "border-[var(--border)]"
          }`}
        >
          <input
            type="radio"
            name="preset"
            className="mt-1"
            checked={presetId === "custom_topk"}
            onChange={() => onPresetIdChange("custom_topk")}
          />
          <span className="flex-1">
            <span className="block text-sm font-medium">{t("newRunPage.customTopK")}</span>
            <span className="mt-0.5 block text-xs text-[var(--muted)]">
              {t("newRunPage.customTopKDescription")}
            </span>
            {presetId === "custom_topk" ? (
              <div className="mt-2 max-w-[120px]">
                <Input value={customTopK} onChange={(e) => onCustomTopKChange(e.target.value)} />
              </div>
            ) : null}
          </span>
        </label>
      </div>
    </div>
  );
}

"use client";

import { useMemo, useState } from "react";
import { useI18n } from "@/lib/locale";
import type { RemoteModelInfo } from "@/lib/types";
import { formatEmbeddingDims } from "@/components/remote-model-picker-utils";
import { Input, Label } from "@/components/ui";

type Props = {
  value: string;
  onChange: (modelId: string) => void;
  items: RemoteModelInfo[];
  loading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  disabled?: boolean;
  /** Shown when list is empty but request succeeded. */
  emptyHint?: string;
};

function formatContext(n: number | null | undefined): string {
  if (n == null || n <= 0) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}k`;
  return String(n);
}

function formatSupportedParams(params: string[] | undefined): string {
  if (!params || params.length === 0) return "—";
  // structured_outputs = JSON Schema; response_format alone = json_object only.
  const highlight = [
    "structured_outputs",
    "response_format",
    "tools",
    "reasoning",
  ];
  const ranked = [
    ...highlight.filter((p) => params.includes(p)),
    ...params.filter((p) => !highlight.includes(p)),
  ];
  const label = (p: string) =>
    p === "structured_outputs"
      ? "structured_outputs (JSON Schema)"
      : p === "response_format" && !params.includes("structured_outputs")
        ? "response_format (json_object)"
        : p;
  const shown = ranked.slice(0, 4).map(label);
  if (ranked.length <= 4) return shown.join(", ");
  return `${shown.join(", ")} +${ranked.length - 4}`;
}

export function RemoteModelPicker({
  value,
  onChange,
  items,
  loading,
  error,
  onRefresh,
  disabled,
  emptyHint,
}: Props) {
  const { t } = useI18n();
  const [filter, setFilter] = useState("");

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) => {
      const dims = formatEmbeddingDims(item);
      const hay = [
        item.id,
        item.name,
        item.modality ?? "",
        ...(item.input_modalities ?? []),
        ...(item.output_modalities ?? []),
        ...(item.supported_parameters ?? []),
        item.context_length != null ? String(item.context_length) : "",
        dims ?? "",
        item.dimension != null ? String(item.dimension) : "",
      ]
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [filter, items]);

  const selectedInList = filtered.some((item) => item.id === value);

  return (
    <div className="grid gap-2">
      <div className="mb-0 flex items-center justify-between gap-2">
        <Label>{t("remoteModelPicker.model")}</Label>
        {onRefresh ? (
          <button
            type="button"
            className="text-xs text-[var(--accent)] underline disabled:opacity-50"
            disabled={disabled || loading}
            onClick={() => onRefresh()}
          >
            {loading
              ? t("remoteModelPicker.loading")
              : t("remoteModelPicker.refresh")}
          </button>
        ) : null}
      </div>

      <Input
        value={filter}
        disabled={disabled}
        placeholder={t("remoteModelPicker.filterPlaceholder")}
        onChange={(e) => setFilter(e.target.value)}
      />

      <Input
        value={value}
        disabled={disabled}
        placeholder={t("remoteModelPicker.manualPlaceholder")}
        onChange={(e) => onChange(e.target.value)}
      />

      <div className="max-h-56 overflow-auto rounded-md border border-[var(--border)] bg-[var(--bg)]/40">
        {loading && items.length === 0 ? (
          <p className="px-3 py-2 text-xs text-[var(--muted)]">
            {t("remoteModelPicker.loading")}
          </p>
        ) : null}
        {!loading && error ? (
          <p className="px-3 py-2 text-xs text-[var(--danger)]">
            {t("remoteModelPicker.failed")}: {error}
          </p>
        ) : null}
        {!loading && !error && filtered.length === 0 ? (
          <p className="px-3 py-2 text-xs text-[var(--muted)]">
            {items.length === 0
              ? (emptyHint ?? t("remoteModelPicker.empty"))
              : t("remoteModelPicker.filterEmpty")}
          </p>
        ) : null}
        {filtered.map((item) => {
          const active = item.id === value;
          const dims = formatEmbeddingDims(item);
          const mrl = (item.dimensions?.length ?? 0) > 1;
          return (
            <button
              key={item.id}
              type="button"
              disabled={disabled}
              className={`flex w-full flex-col gap-0.5 border-b border-[var(--border)]/60 px-3 py-2 text-left text-sm last:border-b-0 hover:bg-[var(--bg)]/80 disabled:opacity-50 ${
                active ? "bg-[var(--accent)]/10" : ""
              }`}
              onClick={() => onChange(item.id)}
            >
              <span className="font-medium text-[var(--fg)]">
                {item.name || item.id}
              </span>
              <span className="text-xs text-[var(--muted)]">
                {item.id !== item.name ? `${item.id} · ` : ""}
                {dims ? (
                  <>
                    {mrl
                      ? t("remoteModelPicker.dimsMrl")
                      : t("remoteModelPicker.dim")}
                    : {dims}
                    {" · "}
                  </>
                ) : null}
                {t("remoteModelPicker.context")}: {formatContext(item.context_length)}
                {" · "}
                {t("remoteModelPicker.modality")}: {item.modality?.trim() || "—"}
                {" · "}
                {t("remoteModelPicker.params")}:{" "}
                {formatSupportedParams(item.supported_parameters)}
              </span>
            </button>
          );
        })}
      </div>

      {value && !selectedInList && filtered.length > 0 ? (
        <p className="text-xs text-[var(--muted)]">
          {t("remoteModelPicker.customSelected")}: {value}
        </p>
      ) : null}

      <p className="text-[11px] text-[var(--muted)]">
        {t("remoteModelPicker.legend")}:{" "}
        {t("remoteModelPicker.name")} — {t("remoteModelPicker.dim")}/
        {t("remoteModelPicker.dimsMrl")} — {t("remoteModelPicker.context")} —{" "}
        {t("remoteModelPicker.modality")} — {t("remoteModelPicker.params")}
      </p>
    </div>
  );
}

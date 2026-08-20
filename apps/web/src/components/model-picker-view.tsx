"use client";

import type { HubModel } from "@/lib/types";
import { Button, ErrorBox, Input, Label } from "@/components/ui";
import { formatModelBytes } from "@/components/model-picker-utils";
import type { useModelPicker } from "@/components/use-model-picker";

type PickerState = ReturnType<typeof useModelPicker>;

type ProgressProps = {
  progress: PickerState["progress"];
  t: PickerState["t"];
};

function ModelPickerProgress({ progress, t }: ProgressProps) {
  if (!progress) return null;
  return (
    <div className="rounded-md border border-[var(--border)] px-3 py-2">
      <div className="mb-1 flex justify-between text-xs text-[var(--muted)]">
        <span>
          {t("modelPicker.stage")}: {progress.stage}
        </span>
        <span>{Math.round(progress.percent)}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded bg-[var(--border)]">
        <div
          className="h-full bg-[var(--accent)] transition-[width]"
          style={{ width: `${Math.min(100, progress.percent)}%` }}
        />
      </div>
      {progress.message ? (
        <p className="mt-1 text-xs text-[var(--muted)]">{progress.message}</p>
      ) : null}
    </div>
  );
}

type CachedChipsProps = {
  rows: Array<{ model_id: string; size_bytes: number | null; in_memory: boolean }>;
  value: string;
  disabled?: boolean;
  loadedIds: Set<string>;
  onChange: (modelId: string) => void;
  t: PickerState["t"];
  title: string;
};

function ModelPickerCachedChips({
  rows,
  value,
  disabled,
  loadedIds,
  onChange,
  t,
  title,
}: CachedChipsProps) {
  if (rows.length === 0) return null;
  return (
    <div>
      <p className="mb-1 text-xs text-[var(--muted)]">{title}</p>
      <div className="flex flex-wrap gap-1">
        {rows.map((row) => (
          <button
            key={row.model_id}
            type="button"
            disabled={disabled}
            className={`rounded border px-2 py-0.5 font-mono text-xs ${
              row.model_id === value
                ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                : "border-[var(--border)]"
            }`}
            onClick={() => onChange(row.model_id)}
            title={
              row.size_bytes != null ? formatModelBytes(row.size_bytes) : undefined
            }
          >
            {row.model_id}
            {row.in_memory || loadedIds.has(row.model_id)
              ? ` · ${t("modelPicker.ready")}`
              : ""}
          </button>
        ))}
      </div>
    </div>
  );
}

type SearchListProps = {
  search: PickerState["search"];
  items: HubModel[];
  value: string;
  disabled?: boolean;
  loading: boolean;
  sizesLoading: boolean;
  loadedIds: Set<string>;
  loadedDimById: Map<string, number>;
  cachedById: Map<string, { size_bytes: number | null; in_memory: boolean }>;
  sizeById: Map<string, number | null>;
  onChange: (modelId: string) => void;
  onLoad: (modelId: string) => void;
  t: PickerState["t"];
};

function ModelPickerSearchList({
  search,
  items,
  value,
  disabled,
  loading,
  sizesLoading,
  loadedIds,
  loadedDimById,
  cachedById,
  sizeById,
  onChange,
  onLoad,
  t,
}: SearchListProps) {
  return (
    <div className="max-h-48 overflow-auto rounded-md border border-[var(--border)]">
      {search.isLoading ? (
        <p className="px-3 py-2 text-sm text-[var(--muted)]">
          {t("modelPicker.searching")}
        </p>
      ) : search.isError ? (
        <p className="px-3 py-2 text-sm text-[var(--danger)]">
          {(search.error as Error).message}
        </p>
      ) : items.length === 0 ? (
        <p className="px-3 py-2 text-sm text-[var(--muted)]">
          {t("modelPicker.noResults")}
        </p>
      ) : (
        <ul className="divide-y divide-[var(--border)]">
          {items.map((m) => {
            const selected = m.id === value;
            const ready = loadedIds.has(m.id);
            const onVolume = cachedById.has(m.id);
            return (
              <li
                key={m.id}
                className={`flex items-center gap-2 px-3 py-2 text-sm ${
                  selected ? "bg-[var(--accent-soft)]" : ""
                }`}
              >
                <button
                  type="button"
                  className="min-w-0 flex-1 text-left"
                  disabled={disabled}
                  onClick={() => onChange(m.id)}
                >
                  <span className="block truncate font-mono text-xs">{m.id}</span>
                  <span className="text-xs text-[var(--muted)]">
                    {onVolume
                      ? t("modelPicker.onVolume")
                      : sizesLoading && !sizeById.has(m.id)
                        ? t("modelPicker.sizeLoading")
                        : sizeById.get(m.id) != null
                          ? t("modelPicker.sizeLabel", {
                              size: formatModelBytes(sizeById.get(m.id)!),
                            })
                          : t("modelPicker.sizeUnknown")}
                    {loadedDimById.get(m.id) != null
                      ? ` · ${t("modelPicker.dimLabel", {
                          dim: String(loadedDimById.get(m.id)),
                        })}`
                      : ""}
                    {ready ? ` · ${t("modelPicker.ready")}` : ""}
                  </span>
                </button>
                <Button
                  type="button"
                  className="shrink-0 px-2 py-1 text-xs"
                  disabled={disabled || loading}
                  onClick={() => void onLoad(m.id)}
                >
                  {ready ? t("modelPicker.use") : t("modelPicker.load")}
                </Button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

type LoadedChipsProps = {
  rows: Array<{ model_id: string; dimension?: number }>;
  value: string;
  disabled?: boolean;
  onChange: (modelId: string) => void;
  t: PickerState["t"];
  title: string;
};

function ModelPickerLoadedChips({
  rows,
  value,
  disabled,
  onChange,
  title,
}: LoadedChipsProps) {
  if (rows.length === 0) return null;
  return (
    <div>
      <p className="mb-1 text-xs text-[var(--muted)]">{title}</p>
      <div className="flex flex-wrap gap-1">
        {rows.map((row) => (
          <button
            key={row.model_id}
            type="button"
            disabled={disabled}
            className={`rounded border px-2 py-0.5 font-mono text-xs ${
              row.model_id === value
                ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                : "border-[var(--border)]"
            }`}
            onClick={() => onChange(row.model_id)}
          >
            {row.model_id}
            {"dimension" in row && typeof row.dimension === "number"
              ? ` · dim ${row.dimension}`
              : ""}
          </button>
        ))}
      </div>
    </div>
  );
}

export function ModelPickerView({
  picker,
  disabled,
}: {
  picker: PickerState;
  disabled?: boolean;
}) {
  const {
    t,
    kind,
    value,
    onChange,
    query,
    setQuery,
    loadError,
    loading,
    progress,
    loaded,
    cached,
    search,
    items,
    loadedIds,
    loadedDimById,
    cachedById,
    sizeById,
    sizesLoading,
    onLoad,
  } = picker;

  return (
    <div className="grid gap-2">
      <Label>
        {kind === "embedding"
          ? t("modelPicker.embeddingLabel")
          : t("modelPicker.rerankLabel")}
      </Label>
      <Input
        value={query}
        disabled={disabled}
        placeholder={t("modelPicker.searchPlaceholder")}
        onChange={(e) => setQuery(e.target.value)}
      />
      {value ? (
        <p className="text-xs text-[var(--muted)]">
          {t("modelPicker.selected")}:{" "}
          <span className="font-mono text-[var(--fg)]">{value}</span>
          {loadedDimById.get(value) != null ? (
            <span className="ml-2">
              {t("modelPicker.dimLabel", {
                dim: String(loadedDimById.get(value)),
              })}
            </span>
          ) : null}
          {loadedIds.has(value) ? (
            <span className="ml-2 text-[var(--accent)]">
              {t("modelPicker.ready")}
            </span>
          ) : cachedById.has(value) ? (
            <span className="ml-2 text-[var(--muted)]">
              {t("modelPicker.onVolume")}
            </span>
          ) : null}
        </p>
      ) : null}

      <ModelPickerProgress progress={progress} t={t} />

      <ModelPickerCachedChips
        rows={cached.data ?? []}
        value={value}
        disabled={disabled}
        loadedIds={loadedIds}
        onChange={onChange}
        t={t}
        title={t("modelPicker.cachedOnVolume")}
      />

      <ModelPickerSearchList
        search={search}
        items={items}
        value={value}
        disabled={disabled}
        loading={loading}
        sizesLoading={sizesLoading}
        loadedIds={loadedIds}
        loadedDimById={loadedDimById}
        cachedById={cachedById}
        sizeById={sizeById}
        onChange={onChange}
        onLoad={onLoad}
        t={t}
      />

      <ModelPickerLoadedChips
        rows={loaded.data ?? []}
        value={value}
        disabled={disabled}
        onChange={onChange}
        t={t}
        title={t("modelPicker.loadedLocally")}
      />

      {loadError ? <ErrorBox message={loadError} /> : null}
    </div>
  );
}

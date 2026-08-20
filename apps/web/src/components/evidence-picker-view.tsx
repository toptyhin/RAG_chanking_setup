"use client";

import type { ChunkContent, EvidenceCandidate } from "@/lib/types";
import {
  evidenceReasonKey,
  GRADE_PRIMARY,
  GRADE_SECONDARY,
} from "@/components/evidence-picker-types";
import type { useEvidencePicker } from "@/components/use-evidence-picker";

type PickerState = ReturnType<typeof useEvidencePicker>;

type RowProps = {
  c: EvidenceCandidate | ChunkContent;
  reason?: string;
  showReason?: boolean;
  relevant: string[];
  grades?: Record<string, number>;
  review: boolean;
  expanded: Record<string, boolean>;
  setExpanded: PickerState["setExpanded"];
  toggleChunk: PickerState["toggleChunk"];
  toggleGrade: PickerState["toggleGrade"];
  t: PickerState["t"];
};

function EvidencePickerRow({
  c,
  reason,
  showReason,
  relevant,
  grades,
  review,
  expanded,
  setExpanded,
  toggleChunk,
  toggleGrade,
  t,
}: RowProps) {
  const chunkId = "chunk_id" in c ? c.chunk_id : "";
  const text = c.text ?? "";
  const checked = relevant.includes(chunkId);
  const grade = grades?.[chunkId] ?? GRADE_SECONDARY;
  const isPrimary = checked && grade >= GRADE_PRIMARY;
  const isOpen = Boolean(expanded[chunkId]);

  return (
    <div className="rounded border border-[var(--border)]/60 p-1.5">
      <div className="flex items-start gap-2 text-xs">
        <label className="flex min-w-0 flex-1 cursor-pointer items-start gap-2">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={checked}
            onChange={() =>
              toggleChunk({
                chunk_id: chunkId,
                doc_id: "doc_id" in c ? c.doc_id : undefined,
                start_char: "start_char" in c ? c.start_char : null,
                end_char: "end_char" in c ? c.end_char : null,
              })
            }
          />
          <span className="min-w-0">
            <code>{chunkId}</code>
            {showReason && reason ? (
              <span className="ml-1 rounded bg-[var(--bg)] px-1 text-[10px] text-[var(--muted)]">
                {t(evidenceReasonKey(reason))}
              </span>
            ) : null}
            <span className="text-[var(--muted)]">
              {" "}
              — {isOpen ? text : `${text.slice(0, 100)}${text.length > 100 ? "…" : ""}`}
            </span>
          </span>
        </label>
        <button
          type="button"
          className="shrink-0 text-[10px] text-[var(--accent)] underline"
          onClick={() =>
            setExpanded((prev) => ({ ...prev, [chunkId]: !prev[chunkId] }))
          }
        >
          {isOpen
            ? t("projectPage.evidenceHideFull")
            : t("projectPage.evidenceShowFull")}
        </button>
        {review && checked ? (
          <button
            type="button"
            className={
              isPrimary
                ? "shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium text-[var(--accent)] ring-1 ring-[var(--accent)]"
                : "shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium text-[var(--muted)] ring-1 ring-[var(--border)]"
            }
            title={t("projectPage.evidenceGradeToggle")}
            onClick={() => toggleGrade(chunkId, isPrimary)}
          >
            {isPrimary
              ? t("projectPage.evidencePrimary")
              : t("projectPage.evidenceSecondary")}
          </button>
        ) : null}
      </div>
    </div>
  );
}

type ListProps = Pick<
  PickerState,
  | "t"
  | "relevant"
  | "grades"
  | "review"
  | "expanded"
  | "setExpanded"
  | "toggleChunk"
  | "toggleGrade"
> & {
  rows: Array<EvidenceCandidate | ChunkContent>;
  showReason?: boolean;
  getReason?: (row: EvidenceCandidate | ChunkContent) => string | undefined;
};

function EvidencePickerList({
  rows,
  showReason,
  getReason,
  ...state
}: ListProps) {
  return (
    <>
      {rows.map((c) => (
        <EvidencePickerRow
          key={"chunk_id" in c ? c.chunk_id : ""}
          c={c}
          reason={getReason?.(c)}
          showReason={showReason}
          {...state}
        />
      ))}
    </>
  );
}

export function EvidencePickerView({ picker }: { picker: PickerState }) {
  const {
    t,
    loading,
    error,
    loadCandidates,
    pinned,
    suggested,
    search,
    setSearch,
    showSearch,
    setShowSearch,
    searchHits,
    ...rowState
  } = picker;

  const listProps = { t, ...rowState };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium text-[var(--muted)]">
          {t("projectPage.evidenceCandidatesTitle")}
        </p>
        <button
          type="button"
          className="text-[10px] text-[var(--accent)] underline"
          onClick={() => void loadCandidates()}
          disabled={loading}
        >
          {t("projectPage.evidenceRefreshCandidates")}
        </button>
      </div>
      {loading ? (
        <p className="text-xs text-[var(--muted)]">
          {t("projectPage.evidenceCandidatesLoading")}
        </p>
      ) : null}
      {error ? <p className="text-xs text-red-600">{error}</p> : null}

      {pinned.length > 0 ? (
        <div>
          <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-[var(--muted)]">
            {t("projectPage.evidencePinnedTitle")}
          </p>
          <div className="flex max-h-40 flex-col gap-1 overflow-y-auto">
            <EvidencePickerList rows={pinned} {...listProps} />
          </div>
        </div>
      ) : null}

      {!loading && suggested.length === 0 && !error ? (
        <p className="text-xs text-[var(--muted)]">
          {t("projectPage.evidenceCandidatesEmpty")}
        </p>
      ) : (
        <div className="flex max-h-48 flex-col gap-1 overflow-y-auto">
          <EvidencePickerList
            rows={suggested}
            showReason
            getReason={(c) => ("reason" in c ? c.reason : undefined)}
            {...listProps}
          />
        </div>
      )}

      <div>
        <button
          type="button"
          className="text-xs text-[var(--accent)] underline"
          onClick={() => setShowSearch((v) => !v)}
        >
          {t("projectPage.evidenceSearchAll")}
        </button>
        {showSearch ? (
          <div className="mt-2 space-y-2">
            <input
              className="w-full rounded border border-[var(--border)] bg-transparent px-2 py-1 text-xs"
              placeholder={t("projectPage.evidenceSearchPlaceholder")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <div className="flex max-h-40 flex-col gap-1 overflow-y-auto">
              <EvidencePickerList
                rows={searchHits.map((c) => ({
                  chunk_id: c.chunk_id,
                  doc_id: c.doc_id,
                  text: c.text,
                  start_char: c.start_char ?? null,
                  end_char: c.end_char ?? null,
                  score: 0,
                  reason: "search",
                }))}
                {...listProps}
              />
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

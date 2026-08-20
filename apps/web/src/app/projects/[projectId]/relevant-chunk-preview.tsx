"use client";

import { useState } from "react";

export function RelevantChunkPreview({
  chunkId,
  text,
  missingLabel,
}: {
  chunkId: string;
  text: string | undefined;
  missingLabel: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-0.5">
      <button
        type="button"
        className="font-mono text-xs text-[var(--accent)] underline-offset-2 hover:underline"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {chunkId}
      </button>
      {open ? (
        <p className="mt-1 whitespace-pre-wrap rounded border border-[var(--border)] bg-[var(--bg)]/60 px-2 py-1.5 text-xs text-[var(--muted)]">
          {text?.trim() ? text : missingLabel}
        </p>
      ) : null}
    </div>
  );
}

"use client";

import {
  useCallback,
  useId,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type KeyboardEvent,
} from "react";

type Props = {
  disabled?: boolean;
  accept?: string;
  multiple?: boolean;
  title: string;
  hint: string;
  busyLabel?: string;
  onFiles: (files: File[]) => void;
};

export function FileDropzone({
  disabled = false,
  accept,
  multiple = true,
  title,
  hint,
  busyLabel,
  onFiles,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();
  const [dragging, setDragging] = useState(false);
  const [fileNames, setFileNames] = useState<string[]>([]);

  const takeFiles = useCallback(
    (list: FileList | File[] | null) => {
      if (!list || disabled) return;
      const files = Array.from(list);
      if (files.length === 0) return;
      setFileNames(files.map((f) => f.name));
      onFiles(files);
    },
    [disabled, onFiles],
  );

  function onDragOver(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (disabled) return;
    setDragging(true);
  }

  function onDragLeave(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
    takeFiles(e.dataTransfer.files);
  }

  function onChange(e: ChangeEvent<HTMLInputElement>) {
    takeFiles(e.target.files);
    // allow re-selecting the same files
    e.target.value = "";
  }

  function onKeyDown(e: KeyboardEvent) {
    if (disabled) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      inputRef.current?.click();
    }
  }

  const selected =
    fileNames.length === 0
      ? null
      : fileNames.length === 1
        ? fileNames[0]
        : `${fileNames[0]} +${fileNames.length - 1}`;

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      aria-labelledby={`${inputId}-title`}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={onKeyDown}
      onDragOver={onDragOver}
      onDragEnter={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      className={`group relative overflow-hidden rounded-xl border-2 border-dashed px-6 py-10 text-center transition duration-200 outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
        disabled
          ? "cursor-not-allowed opacity-60"
          : "cursor-pointer hover:border-[var(--accent)]"
      } ${
        dragging
          ? "scale-[1.01] border-[var(--accent)] bg-[var(--accent-soft)] shadow-[0_0_0_4px_color-mix(in_srgb,var(--accent)_18%,transparent)]"
          : "border-[var(--border)] bg-[color-mix(in_srgb,var(--surface)_70%,var(--accent-soft))]"
      }`}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            "radial-gradient(circle at 20% 20%, color-mix(in srgb, var(--accent) 16%, transparent), transparent 42%), radial-gradient(circle at 85% 70%, color-mix(in srgb, var(--bg-glow-b) 80%, transparent), transparent 45%)",
        }}
      />
      <div className="relative mx-auto flex max-w-md flex-col items-center gap-3">
        <span
          aria-hidden
          className={`flex h-14 w-14 items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--surface)] text-[var(--accent)] shadow-sm transition duration-200 ${
            dragging ? "-translate-y-0.5 scale-105" : "group-hover:-translate-y-0.5"
          }`}
        >
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 16V7" />
            <path d="M8.5 10.5 12 7l3.5 3.5" />
            <path d="M4 16.5V18a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-1.5" />
          </svg>
        </span>
        <div>
          <p
            id={`${inputId}-title`}
            className="text-base font-semibold tracking-tight text-[var(--fg)]"
          >
            {disabled && busyLabel ? busyLabel : title}
          </p>
          <p className="mt-1 text-sm text-[var(--muted)]">{hint}</p>
        </div>
        {selected ? (
          <p className="truncate rounded-md bg-[var(--surface)] px-3 py-1.5 text-xs text-[var(--fg)] ring-1 ring-[var(--border)]">
            {selected}
          </p>
        ) : null}
      </div>
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        className="sr-only"
        multiple={multiple}
        accept={accept}
        disabled={disabled}
        aria-label={title}
        onChange={onChange}
      />
    </div>
  );
}

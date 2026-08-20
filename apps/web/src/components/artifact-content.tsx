"use client";

import { useMemo, useState } from "react";
import type {
  ChunkSetContent,
  CleanCorpusContent,
  IndexRunContent,
  RawBundleContent,
  TestSetContent,
} from "@/lib/types";
import { formatBytes } from "@/lib/format";
import { estimateTokens } from "@/lib/token-estimate";
import { useI18n } from "@/lib/locale";
import { Button, Input, Label } from "@/components/ui";

function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre className="max-h-[32rem] overflow-auto rounded-md border border-[var(--border)] bg-[var(--bg)]/60 p-3 text-xs leading-relaxed">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function SearchField({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  const { t } = useI18n();
  return (
    <div className="mb-3 max-w-sm">
      <Label>{t("artifactContent.filter")}</Label>
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

function RawBundleView({ content }: { content: RawBundleContent }) {
  const { t } = useI18n();
  const files = content.files ?? [];
  return (
    <div>
      <p className="mb-3 text-sm text-[var(--muted)]">
        {t("artifactContent.filesCount", { count: files.length })}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-[var(--muted)]">
              <th className="py-2 pr-3 font-medium">
                {t("artifactContent.name")}
              </th>
              <th className="py-2 pr-3 font-medium">
                {t("artifactContent.type")}
              </th>
              <th className="py-2 pr-3 font-medium">
                {t("artifactContent.size")}
              </th>
              <th className="py-2 font-medium">{t("artifactContent.path")}</th>
            </tr>
          </thead>
          <tbody>
            {files.map((f) => (
              <tr key={f.path} className="border-b border-[var(--border)]">
                <td className="py-2 pr-3">{f.original_name}</td>
                <td className="py-2 pr-3 text-[var(--muted)]">
                  {f.content_type ?? t("common.emDash")}
                </td>
                <td className="py-2 pr-3">{formatBytes(f.size_bytes)}</td>
                <td className="py-2 font-mono text-xs text-[var(--muted)]">
                  {f.path}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CleanCorpusView({ content }: { content: CleanCorpusContent }) {
  const { t } = useI18n();
  const [q, setQ] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);
  const docs = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const all = content.documents ?? [];
    if (!needle) return all;
    return all.filter(
      (d) =>
        d.doc_id.toLowerCase().includes(needle) ||
        d.text.toLowerCase().includes(needle) ||
        (d.source_path ?? "").toLowerCase().includes(needle),
    );
  }, [content.documents, q]);

  return (
    <div>
      {content.prep_pipeline_id ? (
        <p className="mb-2 text-sm text-[var(--muted)]">
          {t("artifactContent.pipeline")} <code>{content.prep_pipeline_id}</code>
        </p>
      ) : null}
      <SearchField
        value={q}
        onChange={setQ}
        placeholder={t("artifactContent.filterDocs")}
      />
      <p className="mb-3 text-sm text-[var(--muted)]">
        {t("artifactContent.showingDocs", {
          shown: docs.length,
          total: (content.documents ?? []).length,
        })}
      </p>
      <ul className="space-y-2">
        {docs.map((d) => {
          const open = openId === d.doc_id;
          return (
            <li
              key={d.doc_id}
              className="rounded-md border border-[var(--border)] bg-[var(--bg)]/40"
            >
              <button
                type="button"
                className="flex w-full items-start justify-between gap-3 px-3 py-2 text-left text-sm"
                onClick={() => setOpenId(open ? null : d.doc_id)}
              >
                <span>
                  <code className="text-[var(--accent)]">{d.doc_id}</code>
                  {d.source_path ? (
                    <span className="ml-2 text-xs text-[var(--muted)]">
                      {d.source_path}
                    </span>
                  ) : null}
                  <span className="mt-1 block text-xs text-[var(--muted)]">
                    {d.text.slice(0, 140)}
                    {d.text.length > 140 ? "…" : ""}
                  </span>
                </span>
                <span className="shrink-0 text-xs text-[var(--muted)]">
                  {open ? t("common.hide") : t("common.expand")}
                </span>
              </button>
              {open ? (
                <pre className="max-h-80 overflow-auto border-t border-[var(--border)] px-3 py-2 text-xs whitespace-pre-wrap">
                  {d.text}
                </pre>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function ChunkSetView({ content }: { content: ChunkSetContent }) {
  const { t } = useI18n();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(0);
  const pageSize = 5;

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const all = content.chunks ?? [];
    if (!needle) return all;
    return all.filter(
      (c) =>
        c.chunk_id.toLowerCase().includes(needle) ||
        c.doc_id.toLowerCase().includes(needle) ||
        c.text.toLowerCase().includes(needle),
    );
  }, [content.chunks, q]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const safePage = Math.min(page, pageCount - 1);
  const pageChunks = filtered.slice(
    safePage * pageSize,
    safePage * pageSize + pageSize,
  );
  const from = filtered.length === 0 ? 0 : safePage * pageSize + 1;
  const to = Math.min(filtered.length, (safePage + 1) * pageSize);

  return (
    <div>
      <SearchField
        value={q}
        onChange={(value) => {
          setQ(value);
          setPage(0);
        }}
        placeholder={t("artifactContent.filterChunks")}
      />
      <p className="mb-3 text-sm text-[var(--muted)]">
        {t("artifactContent.chunkPageRange", {
          from,
          to,
          filtered: filtered.length,
          total: (content.chunks ?? []).length,
        })}
      </p>
      {pageChunks.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">{t("common.none")}</p>
      ) : (
        <ol className="space-y-3">
          {pageChunks.map((c) => {
            const chars = c.text.length;
            const tokens = estimateTokens(c.text);
            return (
              <li
                key={c.chunk_id}
                className="rounded-md border border-[var(--border)] px-3 py-3"
              >
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs text-[var(--muted)]">
                  <code className="font-mono text-[var(--accent)]">
                    {c.chunk_id}
                  </code>
                  <span className="font-mono">{c.doc_id}</span>
                  <span>
                    {t("format.charsAndTokens", { chars, tokens })}
                  </span>
                </div>
                <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed">
                  {c.text}
                </p>
              </li>
            );
          })}
        </ol>
      )}
      {filtered.length > pageSize ? (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button
            type="button"
            disabled={safePage <= 0}
            onClick={() => setPage(safePage - 1)}
          >
            {t("artifactContent.prevPage")}
          </Button>
          <span className="text-sm text-[var(--muted)]">
            {t("artifactContent.pageOf", {
              page: safePage + 1,
              pages: pageCount,
            })}
          </span>
          <Button
            type="button"
            disabled={safePage >= pageCount - 1}
            onClick={() => setPage(safePage + 1)}
          >
            {t("artifactContent.nextPage")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function TestSetView({ content }: { content: TestSetContent }) {
  const { t } = useI18n();
  const [q, setQ] = useState("");
  const queries = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const all = content.queries ?? [];
    if (!needle) return all;
    return all.filter(
      (item) =>
        item.query_id.toLowerCase().includes(needle) ||
        item.text.toLowerCase().includes(needle) ||
        item.relevant_chunk_ids.some((id) => id.toLowerCase().includes(needle)),
    );
  }, [content.queries, q]);

  return (
    <div>
      <SearchField
        value={q}
        onChange={setQ}
        placeholder={t("artifactContent.filterQueries")}
      />
      <p className="mb-3 text-sm text-[var(--muted)]">
        {t("artifactContent.showingQueries", {
          shown: queries.length,
          total: (content.queries ?? []).length,
        })}
      </p>
      <ul className="space-y-3">
        {queries.map((item) => (
          <li
            key={item.query_id}
            className="rounded-md border border-[var(--border)] px-3 py-3"
          >
            <p className="text-xs text-[var(--muted)]">
              <code>{item.query_id}</code>
            </p>
            <p className="mt-1 text-sm font-medium">{item.text}</p>
            <p className="mt-2 text-xs text-[var(--muted)]">
              {t("artifactContent.relevantChunks")}
            </p>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {(item.relevant_chunk_ids ?? []).length === 0 ? (
                <span className="text-xs text-[var(--muted)]">
                  {t("common.none")}
                </span>
              ) : (
                item.relevant_chunk_ids.map((id) => (
                  <code
                    key={id}
                    className="rounded border border-[var(--border)] bg-[var(--bg)]/60 px-1.5 py-0.5 text-xs"
                  >
                    {id}
                  </code>
                ))
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function IndexRunView({ content }: { content: IndexRunContent }) {
  const { t } = useI18n();
  const rows: [string, string][] = [
    ["collection", content.collection_name],
    ["chunk_set_id", content.chunk_set_id],
    ["embedding_model", content.embedding_model],
    ["dimension", String(content.dimension)],
    [
      "build_time_sec",
      content.build_time_sec != null
        ? String(content.build_time_sec)
        : t("common.emDash"),
    ],
    [
      "quantization",
      content.quantization
        ? JSON.stringify(content.quantization)
        : t("artifactContent.quantizationNone"),
    ],
  ];
  return (
    <dl className="grid gap-2 sm:grid-cols-2">
      {rows.map(([k, v]) => (
        <div
          key={k}
          className="rounded-md border border-[var(--border)] px-3 py-2"
        >
          <dt className="text-xs text-[var(--muted)]">{k}</dt>
          <dd className="mt-0.5 break-all font-mono text-sm">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function ArtifactContentView({
  type,
  content,
}: {
  type: string;
  content: unknown;
}) {
  const { t } = useI18n();

  if (content == null) {
    return (
      <p className="text-sm text-[var(--muted)]">
        {t("artifactContent.noContent")}
      </p>
    );
  }

  switch (type) {
    case "raw_bundle":
      return <RawBundleView content={content as RawBundleContent} />;
    case "clean_corpus":
      return <CleanCorpusView content={content as CleanCorpusContent} />;
    case "chunk_set":
      return <ChunkSetView content={content as ChunkSetContent} />;
    case "test_set":
      return <TestSetView content={content as TestSetContent} />;
    case "index_run":
      return <IndexRunView content={content as IndexRunContent} />;
    default:
      return (
        <div>
          <p className="mb-2 text-sm text-[var(--muted)]">
            {t("artifactContent.noTypedViewer", { type })}
          </p>
          <JsonBlock value={content} />
        </div>
      );
  }
}

export function RawJsonToggle({ content }: { content: unknown }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        type="button"
        className="text-sm text-[var(--accent)] underline"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? t("artifactContent.hideRaw") : t("artifactContent.showRaw")}
      </button>
      {open ? (
        <div className="mt-3">
          <JsonBlock value={content} />
        </div>
      ) : null}
    </div>
  );
}

import type { UseMutationResult } from "@tanstack/react-query";
import { Button, ErrorBox } from "@/components/ui";
import { useI18n } from "@/lib/locale";
import type { ChunkPreview } from "@/lib/types";

type ChunkPreviewData = {
  preview: ChunkPreview;
  cleanCorpusId: string;
};

type NewRunChunkPreviewPanelProps = {
  selectedCleanCorpusId: string;
  chunkLabPreview: UseMutationResult<ChunkPreviewData, Error, void, unknown>;
  chunkLabPreviewFresh: boolean;
};

export function NewRunChunkPreviewPanel({
  selectedCleanCorpusId,
  chunkLabPreview,
  chunkLabPreviewFresh,
}: NewRunChunkPreviewPanelProps) {
  const { t } = useI18n();

  return (
    <div className="rounded-lg border border-[var(--border)] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">{t("newRunPage.chunkPreviewTitle")}</p>
          <p className="mt-1 text-xs text-[var(--muted)]">
            {t("newRunPage.chunkPreviewDescription")}
          </p>
        </div>
        <Button
          type="button"
          disabled={chunkLabPreview.isPending || !selectedCleanCorpusId}
          onClick={() => chunkLabPreview.mutate()}
        >
          {chunkLabPreview.isPending ? t("chunkerForm.previewing") : t("chunkerForm.preview")}
        </Button>
      </div>
      {chunkLabPreview.isError ? (
        <ErrorBox message={(chunkLabPreview.error as Error).message} />
      ) : null}
      {chunkLabPreview.data && chunkLabPreviewFresh ? (
        <div className="mt-3">
          <p className="text-xs text-[var(--muted)]">
            {t("chunkerForm.previewStats", {
              count: chunkLabPreview.data.preview.chunk_count,
              average: chunkLabPreview.data.preview.size.average_chars,
              averageTokens: chunkLabPreview.data.preview.size.average_tokens,
              p50: chunkLabPreview.data.preview.size.p50_chars,
              p50Tokens: chunkLabPreview.data.preview.size.p50_tokens,
              p95: chunkLabPreview.data.preview.size.p95_chars,
              p95Tokens: chunkLabPreview.data.preview.size.p95_tokens,
              max: chunkLabPreview.data.preview.size.max_chars,
              maxTokens: chunkLabPreview.data.preview.size.max_tokens,
            })}
          </p>
          <p className="mt-1 text-xs text-[var(--muted)]">
            {t("chunkerForm.tokensApproxNote")}
          </p>
          <ol className="mt-2 grid gap-2 sm:grid-cols-2">
            {chunkLabPreview.data.preview.samples.slice(0, 4).map((sample, index) => (
              <li
                key={sample.chunk_id}
                className="rounded border border-[var(--border)] px-3 py-2"
              >
                <p className="text-xs font-medium text-[var(--muted)]">
                  {t("chunkerForm.previewSample", {
                    n: index + 1,
                    size: sample.size_chars,
                    tokens: sample.size_tokens,
                  })}
                </p>
                <p className="mt-1 whitespace-pre-wrap break-words text-sm">{sample.text}</p>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </div>
  );
}

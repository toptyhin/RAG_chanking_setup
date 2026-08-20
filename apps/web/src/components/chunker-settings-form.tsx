"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useMemo, useState } from "react";
import {
  createChunkSet,
  getChunkSetContent,
  getCurrentEmbedding,
  getEmbeddingConfig,
  listChunkers,
  listLoadedEmbeddings,
  previewChunkSet,
  type ChunkerProviderId,
  type CreateChunkSetBody,
} from "@/lib/api";
import type { Artifact } from "@/lib/types";
import { resolveEmbeddingDimensionForModel, maxCharsFromMeta, maxTokensFromMeta } from "@/lib/chunk-embedding-fit";
import { activeEmbeddingModelId } from "@/lib/embedding";
import { artifactDisplayName } from "@/lib/format";
import { useI18n } from "@/lib/locale";
import type { TranslationKey } from "@/i18n";
import { ArtifactContentView } from "@/components/artifact-content";
import { ChunkEmbeddingDimWarning } from "@/components/chunk-embedding-dim-warning";
import {
  AdvancedSettings,
  Affects,
  Button,
  ErrorBox,
  Label,
  Select,
  TabBar,
  WhyItMatters,
} from "@/components/ui";
import type {
  ChunkletFormState,
  ReferenceFormState,
  SemchunkFormState,
} from "@/components/chunker-form-types";

const PROVIDER_COPY: Record<
  ChunkerProviderId,
  {
    summary: TranslationKey;
    features: TranslationKey[];
  }
> = {
  semchunk: {
    summary: "chunkerForm.providers.semchunk.summary",
    features: [
      "chunkerForm.providers.semchunk.feature1",
      "chunkerForm.providers.semchunk.feature2",
      "chunkerForm.providers.semchunk.feature3",
      "chunkerForm.providers.semchunk.feature4",
    ],
  },
  chunklet: {
    summary: "chunkerForm.providers.chunklet.summary",
    features: [
      "chunkerForm.providers.chunklet.feature1",
      "chunkerForm.providers.chunklet.feature2",
      "chunkerForm.providers.chunklet.feature3",
      "chunkerForm.providers.chunklet.feature4",
    ],
  },
  reference_fixed: {
    summary: "chunkerForm.providers.reference_fixed.summary",
    features: [
      "chunkerForm.providers.reference_fixed.feature1",
      "chunkerForm.providers.reference_fixed.feature2",
      "chunkerForm.providers.reference_fixed.feature3",
      "chunkerForm.providers.reference_fixed.feature4",
    ],
  },
};

const SemchunkFields = dynamic(
  () =>
    import("@/components/chunker-fields").then((m) => m.SemchunkFields),
  { ssr: false },
);
const ChunkletFields = dynamic(
  () =>
    import("@/components/chunker-fields").then((m) => m.ChunkletFields),
  { ssr: false },
);
const ReferenceFields = dynamic(
  () =>
    import("@/components/chunker-fields").then((m) => m.ReferenceFields),
  { ssr: false },
);

const PROVIDER_ORDER: ChunkerProviderId[] = [
  "semchunk",
  "chunklet",
  "reference_fixed",
];

const DEFAULT_SEMCHUNK: SemchunkFormState = {
  chunk_size: 512,
  overlap: null,
  token_counter: "words",
};

const DEFAULT_CHUNKLET: ChunkletFormState = {
  mode: "document",
  lang: "auto",
  max_tokens: null,
  max_sentences: 5,
  max_section_breaks: null,
  max_lines: null,
  max_functions: null,
  overlap_percent: 20,
  offset: 0,
  include_comments: true,
  docstring_mode: "all",
  strict: true,
  token_counter: "words",
};

const DEFAULT_REFERENCE: ReferenceFormState = {
  size: 512,
  overlap: 64,
};

function buildBody(
  provider: ChunkerProviderId,
  cleanCorpusId: string,
  semchunk: SemchunkFormState,
  chunklet: ChunkletFormState,
  reference: ReferenceFormState,
): CreateChunkSetBody {
  if (provider === "semchunk") {
    return {
      clean_corpus_id: cleanCorpusId,
      provider,
      chunk_size: semchunk.chunk_size,
      overlap: semchunk.overlap,
      token_counter: semchunk.token_counter,
    };
  }
  if (provider === "chunklet") {
    const base: CreateChunkSetBody = {
      clean_corpus_id: cleanCorpusId,
      provider,
      mode: chunklet.mode,
      token_counter: chunklet.token_counter,
    };
    if (chunklet.mode === "code") {
      return {
        ...base,
        max_tokens: chunklet.max_tokens,
        max_lines: chunklet.max_lines,
        max_functions: chunklet.max_functions ?? 1,
        include_comments: chunklet.include_comments,
        docstring_mode: chunklet.docstring_mode,
        strict: chunklet.strict,
      };
    }
    return {
      ...base,
      lang: chunklet.lang,
      max_tokens: chunklet.max_tokens,
      max_sentences: chunklet.max_sentences,
      max_section_breaks: chunklet.max_section_breaks,
      overlap_percent: chunklet.overlap_percent,
      offset: chunklet.offset,
    };
  }
  return {
    clean_corpus_id: cleanCorpusId,
    provider: "reference_fixed",
    size: reference.size,
    overlap: reference.overlap,
  };
}

function artifactLabel(a: Artifact): string {
  return artifactDisplayName(a.type, a.meta, a.id);
}

function effectiveChunkSize(
  provider: ChunkerProviderId | "",
  semchunk: SemchunkFormState,
  chunklet: ChunkletFormState,
  reference: ReferenceFormState,
): number | null {
  if (provider === "semchunk") return semchunk.chunk_size;
  if (provider === "reference_fixed") return reference.size;
  if (provider === "chunklet") {
    return typeof chunklet.max_tokens === "number" ? chunklet.max_tokens : null;
  }
  return null;
}

type Props = {
  projectId: string;
  cleanCorpora: Artifact[];
  cleanId: string;
  onCleanIdChange: (id: string) => void;
  onSuccess: () => void | Promise<void>;
};

export function ChunkerSettingsForm({
  projectId,
  cleanCorpora,
  cleanId,
  onCleanIdChange,
  onSuccess,
}: Props) {
  const { t } = useI18n();
  const [provider, setProvider] = useState<ChunkerProviderId | "">("semchunk");
  const [semchunk, setSemchunk] = useState(DEFAULT_SEMCHUNK);
  const [chunklet, setChunklet] = useState(DEFAULT_CHUNKLET);
  const [reference, setReference] = useState(DEFAULT_REFERENCE);
  const [previewKey, setPreviewKey] = useState("");
  const [saved, setSaved] = useState<{
    key: string;
    artifact: Artifact;
    chunk_count: number;
  } | null>(null);

  const providersQuery = useQuery({
    queryKey: ["chunkers"],
    queryFn: listChunkers,
  });

  const currentEmbedding = useQuery({
    queryKey: ["models", "embedding", "current"],
    queryFn: getCurrentEmbedding,
  });
  const embeddingConfig = useQuery({
    queryKey: ["embedding", "config"],
    queryFn: getEmbeddingConfig,
  });
  const loadedEmbeddings = useQuery({
    queryKey: ["models", "embedding", "loaded"],
    queryFn: listLoadedEmbeddings,
  });

  const providers = useMemo(() => {
    const byId = new Map((providersQuery.data ?? []).map((p) => [p.id, p]));
    return PROVIDER_ORDER.map((id) => {
      const info = byId.get(id);
      return {
        id,
        label: info?.label ?? id,
        available: info?.available ?? true,
        unavailable_reason: info?.unavailable_reason ?? null,
      };
    });
  }, [providersQuery.data]);

  const selectedMeta = providers.find((p) => p.id === provider);
  const corpusId = cleanId || cleanCorpora[0]?.id || "";
  const chunkSize = effectiveChunkSize(provider, semchunk, chunklet, reference);
  const embeddingModelId =
    activeEmbeddingModelId(embeddingConfig.data) ||
    currentEmbedding.data?.model_id ||
    "";
  const embeddingDimension = resolveEmbeddingDimensionForModel(
    embeddingModelId,
    loadedEmbeddings.data,
    currentEmbedding.data,
  );
  const currentBody = useMemo(
    () =>
      provider && corpusId
        ? buildBody(provider, corpusId, semchunk, chunklet, reference)
        : null,
    [provider, corpusId, semchunk, chunklet, reference],
  );
  const currentKey = currentBody ? JSON.stringify(currentBody) : "";

  const preview = useMutation({
    mutationFn: async () => {
      if (!currentBody) throw new Error(t("projectPage.noCleanCorpus"));
      const result = await previewChunkSet(projectId, {
        ...currentBody,
        preview_count: 5,
      });
      return { result, key: currentKey };
    },
    onSuccess: (data) => {
      setSaved(null);
      setPreviewKey(data.key);
    },
  });
  const previewFresh = Boolean(currentKey) && previewKey === currentKey;
  const showSaved = saved != null && saved.key === currentKey;
  const showDraft = Boolean(preview.data && previewFresh && !showSaved);

  const chunk = useMutation({
    mutationFn: () => {
      if (!corpusId) throw new Error(t("projectPage.noCleanCorpus"));
      if (!provider) throw new Error(t("chunkerForm.selectLibrary"));
      if (!previewFresh) throw new Error(t("chunkerForm.previewRequired"));
      return createChunkSet(
        projectId,
        buildBody(provider, corpusId, semchunk, chunklet, reference),
      );
    },
    onSuccess: async (data) => {
      setSaved({
        key: currentKey,
        artifact: data.artifact,
        chunk_count: data.chunk_count,
      });
      setPreviewKey("");
      preview.reset();
      await onSuccess();
    },
  });

  const savedContent = useQuery({
    queryKey: ["artifacts", saved?.artifact.id, "content"],
    queryFn: () => getChunkSetContent(saved!.artifact.id),
    enabled: showSaved && Boolean(saved?.artifact.id),
  });

  const confirmDisabledReason = ((): TranslationKey | null => {
    if (chunk.isPending) return null;
    if (showSaved) return null;
    if (!corpusId) return "projectPage.noCleanCorpus";
    if (!provider) return "chunkerForm.selectLibrary";
    if (selectedMeta?.available === false) return "chunkerForm.confirmUnavailable";
    if (!previewFresh) {
      return preview.data
        ? "chunkerForm.previewStale"
        : "chunkerForm.previewRequired";
    }
    return null;
  })();
  const confirmDisabled =
    confirmDisabledReason != null || chunk.isPending || showSaved;

  const libraryTabs = providers.map((p) => ({
    id: p.id,
    label: p.available
      ? p.label
      : `${p.label} (${t("chunkerForm.unavailable")})`,
    description: p.unavailable_reason ?? undefined,
  }));

  return (
    <div>
      <h3 className="text-sm font-semibold">{t("chunkerForm.title")}</h3>
      <div className="mt-2">
        <Label>{t("projectPage.cleanCorpus")}</Label>
        <Select
          value={cleanId || cleanCorpora[0]?.id || ""}
          onChange={(e) => onCleanIdChange(e.target.value)}
        >
          {cleanCorpora.length === 0 ? (
            <option value="">{t("projectPage.noCleanCorpus")}</option>
          ) : null}
          {cleanCorpora.map((a) => (
            <option key={a.id} value={a.id}>
              {artifactLabel(a)}
            </option>
          ))}
        </Select>
      </div>

      <div className="mt-4 rounded-lg border border-[var(--accent)]/35 bg-[var(--accent-soft)] p-4">
        <p className="text-sm font-medium">{t("chunkerForm.recommendedTitle")}</p>
        <p className="mt-1 text-sm text-[var(--muted)]">
          {t("chunkerForm.recommendedDescription")}
        </p>
        <Affects label={t("help.affects")}>{t("chunkerForm.recommendedAffects")}</Affects>
      </div>

      <WhyItMatters label={t("help.whyItMatters")}>
        {t("chunkerForm.whyItMatters")}
      </WhyItMatters>

      <div className="mt-4">
      <AdvancedSettings
        label={t("chunkerForm.advanced")}
        description={t("chunkerForm.advancedDescription")}
      >
      <div>
        <Label>{t("chunkerForm.library")}</Label>
        <div className="mt-1">
          <TabBar
            className="mb-3"
            tabs={libraryTabs}
            value={(provider || "semchunk") as ChunkerProviderId}
            onChange={(id) => {
              const meta = providers.find((p) => p.id === id);
              if (meta && !meta.available) return;
              setProvider(id);
            }}
          />
        </div>
      </div>

      {provider ? (
        <div className="mb-3 rounded-lg border border-[var(--border)] bg-[color-mix(in_srgb,var(--accent-soft)_55%,var(--surface))] px-4 py-3">
          <p className="text-sm leading-relaxed text-[var(--fg)]">
            {t(PROVIDER_COPY[provider].summary)}
          </p>
          <p className="mt-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            {t("chunkerForm.featuresTitle")}
          </p>
          <ul className="mt-1.5 list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
            {PROVIDER_COPY[provider].features.map((key) => (
              <li key={key}>{t(key)}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {provider && selectedMeta && !selectedMeta.available ? (
        <p className="mt-2 text-sm text-[var(--danger,#b42318)]">
          {selectedMeta.unavailable_reason || t("chunkerForm.unavailable")}
        </p>
      ) : null}

      {provider === "semchunk" ? (
        <div className="mt-1">
          <SemchunkFields value={semchunk} onChange={setSemchunk} />
        </div>
      ) : null}
      {provider === "chunklet" ? (
        <div className="mt-1">
          <ChunkletFields value={chunklet} onChange={setChunklet} />
        </div>
      ) : null}
      {provider === "reference_fixed" ? (
        <div className="mt-1">
          <ReferenceFields value={reference} onChange={setReference} />
        </div>
      ) : null}
      </AdvancedSettings>
      </div>

      <ChunkEmbeddingDimWarning
        className="mt-3"
        embeddingDimension={embeddingDimension}
        chunkSize={chunkSize}
      />

      <div className="mt-3 flex flex-wrap gap-2">
        <Button
          type="button"
          disabled={
            preview.isPending ||
            !provider ||
            !corpusId ||
            selectedMeta?.available === false
          }
          onClick={() => preview.mutate()}
        >
          {preview.isPending
            ? t("chunkerForm.previewing")
            : t("chunkerForm.preview")}
        </Button>
        <span
          className="inline-flex"
          title={
            confirmDisabledReason ? t(confirmDisabledReason) : undefined
          }
        >
          <Button
            type="button"
            disabled={confirmDisabled}
            onClick={() => chunk.mutate()}
          >
            {chunk.isPending
              ? t("projectPage.chunking")
              : t("chunkerForm.confirm")}
          </Button>
        </span>
      </div>
      {confirmDisabledReason ? (
        <p className="mt-2 text-xs text-[var(--muted)]" role="status">
          {t(confirmDisabledReason)}
        </p>
      ) : null}
      {preview.isError ? (
        <ErrorBox message={(preview.error as Error).message} />
      ) : null}
      {showDraft ? (
        <div className="mt-3 rounded-lg border border-[var(--border)] bg-[var(--bg)]/40 p-4">
          <p className="text-sm font-semibold">
            {t("chunkerForm.previewTitle")}
          </p>
          <p className="mt-1 text-xs text-[var(--muted)]">
            {t("chunkerForm.previewStats", {
              count: preview.data!.result.chunk_count,
              average: preview.data!.result.size.average_chars,
              averageTokens: preview.data!.result.size.average_tokens,
              p50: preview.data!.result.size.p50_chars,
              p50Tokens: preview.data!.result.size.p50_tokens,
              p95: preview.data!.result.size.p95_chars,
              p95Tokens: preview.data!.result.size.p95_tokens,
              max: preview.data!.result.size.max_chars,
              maxTokens: preview.data!.result.size.max_tokens,
            })}
          </p>
          <p className="mt-1 text-xs text-[var(--muted)]">
            {t("chunkerForm.tokensApproxNote")}
          </p>
          <ol className="mt-3 space-y-2">
            {preview.data!.result.samples.map((sample, index) => (
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
                <p className="mt-1 whitespace-pre-wrap break-words text-sm">
                  {sample.text}
                </p>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
      {chunk.isError ? (
        <ErrorBox message={(chunk.error as Error).message} />
      ) : null}
      {showSaved && saved ? (
        <div className="mt-3 rounded-lg border border-[var(--border)] bg-[var(--bg)]/40 p-4">
          <p className="text-sm font-semibold">
            {t("chunkerForm.savedTitle")}
          </p>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {t("projectPage.chunkSetCreated", {
              id: artifactDisplayName(
                saved.artifact.type,
                saved.artifact.meta,
                saved.artifact.id,
              ),
              count: saved.chunk_count,
            })}
            {maxCharsFromMeta(saved.artifact.meta) != null
              ? ` · ${
                  maxTokensFromMeta(saved.artifact.meta) != null
                    ? t("format.maxLength", {
                        chars: maxCharsFromMeta(saved.artifact.meta)!,
                        tokens: maxTokensFromMeta(saved.artifact.meta)!,
                      })
                    : t("format.maxChars", {
                        count: maxCharsFromMeta(saved.artifact.meta)!,
                      })
                }`
              : null}{" "}
            <Link
              href={`/projects/${projectId}/artifacts/${saved.artifact.id}`}
              className="text-[var(--accent)] underline"
            >
              {t("common.view")}
            </Link>
            {" · "}
            <Link
              href={`/projects/${projectId}/test-set`}
              className="text-[var(--accent)] underline"
            >
              {t("chunkerForm.continueTestSet")}
            </Link>
          </p>
          {savedContent.isPending ? (
            <p className="mt-3 text-sm text-[var(--muted)]">
              {t("chunkerForm.savedLoading")}
            </p>
          ) : null}
          {savedContent.isError ? (
            <div className="mt-3">
              <ErrorBox message={(savedContent.error as Error).message} />
            </div>
          ) : null}
          {savedContent.data ? (
            <div className="mt-3">
              <ArtifactContentView
                type="chunk_set"
                content={savedContent.data}
              />
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

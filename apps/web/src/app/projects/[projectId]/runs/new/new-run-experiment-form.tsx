import { usePathname } from "next/navigation";
import { useMemo, type FormEvent } from "react";
import { ChunkEmbeddingDimWarning } from "@/components/chunk-embedding-dim-warning";
import { Button, Callout, ErrorBox, Section } from "@/components/ui";
import { chunkSizeFromMeta } from "@/lib/chunk-embedding-fit";
import { useI18n } from "@/lib/locale";
import { NewRunArtifactFields } from "./new-run-artifact-fields";
import { NewRunChunkPreviewPanel } from "./new-run-chunk-preview-panel";
import { NewRunPresetPicker } from "./new-run-preset-picker";
import { NewRunRetrievalAdvanced } from "./new-run-retrieval-advanced";
import type { NewRunFormState } from "./use-new-run-form";

type NewRunExperimentFormProps = {
  form: NewRunFormState;
};

export function NewRunExperimentForm({ form }: NewRunExperimentFormProps) {
  const { t } = useI18n();
  const pathname = usePathname();

  const comparedChunkSize = useMemo(() => {
    if (form.labMode === "chunk") {
      return 1024; // Chunk Lab sweeps 256 / 512 / 1024
    }
    if (form.labMode === "retrieval") {
      return chunkSizeFromMeta(form.selectedChunkSet?.meta);
    }
    return null;
  }, [form.labMode, form.selectedChunkSet?.meta]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    form.start.mutate();
  }

  return (
    <Section
      title={t("newRunPage.experimentTitle")}
      description={t("newRunPage.experimentDescription")}
    >
      <form onSubmit={onSubmit} className="grid gap-5">
        <NewRunArtifactFields
          labMode={form.labMode}
          rawBundles={form.rawBundles}
          cleanCorpora={form.cleanCorpora}
          chunkSets={form.chunkSets}
          testSets={form.testSets}
          rawBundleId={form.rawBundleId}
          onRawBundleIdChange={form.setRawBundleId}
          cleanCorpusId={form.cleanCorpusId}
          onCleanCorpusIdChange={form.setCleanCorpusId}
          chunkSetId={form.chunkSetId}
          onChunkSetIdChange={form.setChunkSetId}
          testSetId={form.testSetId}
          onTestSetIdChange={form.setTestSetId}
        />

        <ChunkEmbeddingDimWarning
          embeddingDimension={form.embeddingDimensionForRun}
          chunkSize={comparedChunkSize}
        />

        {form.labMode === "chunk" ? (
          <Callout tone="warning">
            <strong>{t("newRunPage.chunkDisclaimerTitle")}</strong>{" "}
            {t("newRunPage.chunkDisclaimer")}
          </Callout>
        ) : null}

        {form.labMode !== "retrieval" ? (
          <Callout>
            {t(
              form.labMode === "prep"
                ? "newRunPage.prepComparison"
                : "newRunPage.chunkComparison",
            )}
          </Callout>
        ) : null}

        {form.labMode === "chunk" ? (
          <NewRunChunkPreviewPanel
            selectedCleanCorpusId={form.selectedCleanCorpusId}
            chunkLabPreview={form.chunkLabPreview}
            chunkLabPreviewFresh={form.chunkLabPreviewFresh}
          />
        ) : null}

        {form.labMode === "retrieval" ? (
          <NewRunPresetPicker
            presetId={form.presetId}
            onPresetIdChange={form.setPresetId}
            customTopK={form.customTopK}
            onCustomTopKChange={form.setCustomTopK}
          />
        ) : null}

        <Callout>
          <strong>{t("newRunPage.configCount", { count: form.configCount })}</strong>{" "}
          {t("newRunPage.configCountHint")}
        </Callout>

        {form.labMode === "retrieval" ? (
          <NewRunRetrievalAdvanced
            pathname={pathname}
            embeddingModelOverride={form.embeddingModelOverride}
            onEmbeddingModelOverrideChange={form.setEmbeddingModelOverride}
            embeddingModelId={form.embeddingModelId}
            embeddingConfig={form.embeddingConfig}
            currentEmbedding={form.currentEmbedding}
            embeddingDimensionForRun={form.embeddingDimensionForRun}
            enableRerank={form.enableRerank}
            onEnableRerankChange={form.setEnableRerank}
            rerankModelId={form.rerankModelId}
            selectedChunkSet={form.selectedChunkSet}
            qdrantSummary={form.qdrantSummary}
            fixedAxes={form.fixedAxes}
            sweptAxes={form.sweptAxes}
            quantization={form.quantization}
            onQuantizationChange={form.setQuantization}
            startPending={form.start.isPending}
          />
        ) : null}

        <Callout tone={form.configCount > 8 ? "warning" : "info"}>
          {t("newRunPage.resultHint")}
          {form.configCount > 8 ? ` ${t("newRunPage.costWarning")}` : null}
        </Callout>

        <div>
          <Button
            type="submit"
            disabled={
              form.start.isPending ||
              (form.labMode === "chunk" && !form.chunkLabPreviewFresh)
            }
          >
            {form.start.isPending ? t("newRunPage.starting") : t("newRunPage.start")}
          </Button>
          {form.start.isError ? (
            <ErrorBox message={(form.start.error as Error).message} />
          ) : null}
        </div>
      </form>
    </Section>
  );
}

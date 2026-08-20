import Link from "next/link";
import {
  AdvancedSettings,
  Input,
  Label,
  Select,
} from "@/components/ui";
import { activeEmbeddingLabel } from "@/lib/embedding";
import { useI18n } from "@/lib/locale";
import { withReturnTo } from "@/lib/return-to";
import type { QuantizationChoice } from "@/lib/presets";
import type { Artifact } from "@/lib/types";
import { chunkingSummary } from "./new-run-utils";
import type { NewRunFormState } from "./use-new-run-form";

type NewRunRetrievalAdvancedProps = {
  pathname: string;
  embeddingModelOverride: string;
  onEmbeddingModelOverrideChange: (value: string) => void;
  embeddingModelId: string;
  embeddingConfig: NewRunFormState["embeddingConfig"];
  currentEmbedding: NewRunFormState["currentEmbedding"];
  embeddingDimensionForRun: number | null;
  enableRerank: boolean;
  onEnableRerankChange: (enabled: boolean) => void;
  rerankModelId: string;
  selectedChunkSet: Artifact | undefined;
  qdrantSummary: string;
  fixedAxes: string;
  sweptAxes: string;
  quantization: QuantizationChoice;
  onQuantizationChange: (value: QuantizationChoice) => void;
  startPending: boolean;
};

export function NewRunRetrievalAdvanced({
  pathname,
  embeddingModelOverride,
  onEmbeddingModelOverrideChange,
  embeddingModelId,
  embeddingConfig,
  currentEmbedding,
  embeddingDimensionForRun,
  enableRerank,
  onEnableRerankChange,
  rerankModelId,
  selectedChunkSet,
  qdrantSummary,
  fixedAxes,
  sweptAxes,
  quantization,
  onQuantizationChange,
  startPending,
}: NewRunRetrievalAdvancedProps) {
  const { t } = useI18n();

  return (
    <AdvancedSettings
      label={t("newRunPage.advanced")}
      description={t("newRunPage.advancedDescription")}
    >
      <div className="grid gap-5">
        <div>
          <Label>{t("newRunPage.modelForRun")}</Label>
          <Input
            value={embeddingModelOverride || embeddingModelId}
            onChange={(event) => onEmbeddingModelOverrideChange(event.target.value)}
            placeholder={t("newRunPage.modelForRunPlaceholder")}
          />
          <p className="mt-1 text-xs text-[var(--muted)]">
            {t("newRunPage.modelForRunHint")}{" "}
            <Link
              href={withReturnTo("/settings/connections?tab=embedding", pathname)}
              className="text-[var(--accent)] underline"
            >
              {t("newRunPage.openConnections")}
            </Link>
          </p>
        </div>

        <div className="rounded-md border border-[var(--border)] px-3 py-3">
          <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
            <p className="text-sm font-medium">{t("newRunPage.summaryTitle")}</p>
            <Link
              href={withReturnTo("/settings/connections?tab=embedding", pathname)}
              className="text-xs text-[var(--accent)] underline"
            >
              {t("newRunPage.summaryChangeModels")}
            </Link>
          </div>
          <dl className="grid gap-2 text-sm">
            <div className="grid gap-0.5 sm:grid-cols-[9rem_1fr]">
              <dt className="text-[var(--muted)]">{t("newRunPage.summaryEmbedding")}</dt>
              <dd className="font-mono text-xs break-all">
                {embeddingModelOverride || activeEmbeddingLabel(embeddingConfig.data)}
                {embeddingDimensionForRun != null
                  ? ` · dim ${embeddingDimensionForRun}`
                  : currentEmbedding.data?.dimension != null
                    ? ` · dim ${currentEmbedding.data.dimension}`
                    : ""}
              </dd>
            </div>
            <div className="grid gap-0.5 sm:grid-cols-[9rem_1fr]">
              <dt className="text-[var(--muted)]">{t("newRunPage.summaryRerank")}</dt>
              <dd className="font-mono text-xs break-all">
                {enableRerank ? rerankModelId : t("newRunPage.summaryRerankOff")}
              </dd>
            </div>
            <div className="grid gap-0.5 sm:grid-cols-[9rem_1fr]">
              <dt className="text-[var(--muted)]">{t("newRunPage.summaryChunking")}</dt>
              <dd className="text-xs">
                {selectedChunkSet ? chunkingSummary(selectedChunkSet.meta, t) : "—"}
              </dd>
            </div>
            <div className="grid gap-0.5 sm:grid-cols-[9rem_1fr]">
              <dt className="text-[var(--muted)]">{t("newRunPage.summaryQdrant")}</dt>
              <dd className="text-xs">{qdrantSummary}</dd>
            </div>
            <div className="grid gap-0.5 sm:grid-cols-[9rem_1fr]">
              <dt className="text-[var(--muted)]">{t("newRunPage.fixedAxes")}</dt>
              <dd className="font-mono text-xs">{fixedAxes}</dd>
            </div>
            <div className="grid gap-0.5 sm:grid-cols-[9rem_1fr]">
              <dt className="text-[var(--muted)]">{t("newRunPage.sweptAxes")}</dt>
              <dd className="font-mono text-xs">{sweptAxes}</dd>
            </div>
          </dl>
        </div>

        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            className="mt-1"
            checked={enableRerank}
            disabled={startPending}
            onChange={(e) => onEnableRerankChange(e.target.checked)}
          />
          <span>
            <span className="font-medium">{t("newRunPage.enableRerank")}</span>
            <span className="mt-0.5 block text-xs text-[var(--muted)]">
              {t("newRunPage.enableRerankDescription")}
            </span>
            <span className="mt-1 block font-mono text-xs break-all">
              {rerankModelId}
              {" · "}
              <Link
                href={withReturnTo("/settings/connections?tab=rerank", pathname)}
                className="font-sans text-[var(--accent)] underline"
              >
                {t("newRunPage.summaryChangeModels")}
              </Link>
            </span>
          </span>
        </label>

        <div>
          <Label>{t("newRunPage.quantization")}</Label>
          <p className="mt-0.5 mb-2 text-xs text-[var(--muted)]">
            {t("newRunPage.quantizationDescription")}
          </p>
          <Select
            value={quantization}
            disabled={startPending}
            onChange={(e) => onQuantizationChange(e.target.value as QuantizationChoice)}
          >
            <option value="none">{t("newRunPage.quantizationNone")}</option>
            <option value="binary">{t("newRunPage.quantizationBinary")}</option>
            <option value="binary+rescore">{t("newRunPage.quantizationBinaryRescore")}</option>
            <option value="scalar">{t("newRunPage.quantizationScalar")}</option>
            <option value="scalar+rescore">{t("newRunPage.quantizationScalarRescore")}</option>
            <option value="compare">{t("newRunPage.quantizationCompare")}</option>
          </Select>
        </div>
      </div>
    </AdvancedSettings>
  );
}

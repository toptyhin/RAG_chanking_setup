import { Label, Select } from "@/components/ui";
import { artifactDisplayName } from "@/lib/format";
import { useI18n } from "@/lib/locale";
import type { Artifact } from "@/lib/types";
import { artifactLabel, type LabMode } from "./new-run-utils";

type NewRunArtifactFieldsProps = {
  labMode: LabMode;
  rawBundles: Artifact[];
  cleanCorpora: Artifact[];
  chunkSets: Artifact[];
  testSets: Artifact[];
  rawBundleId: string;
  onRawBundleIdChange: (id: string) => void;
  cleanCorpusId: string;
  onCleanCorpusIdChange: (id: string) => void;
  chunkSetId: string;
  onChunkSetIdChange: (id: string) => void;
  testSetId: string;
  onTestSetIdChange: (id: string) => void;
};

export function NewRunArtifactFields({
  labMode,
  rawBundles,
  cleanCorpora,
  chunkSets,
  testSets,
  rawBundleId,
  onRawBundleIdChange,
  cleanCorpusId,
  onCleanCorpusIdChange,
  chunkSetId,
  onChunkSetIdChange,
  testSetId,
  onTestSetIdChange,
}: NewRunArtifactFieldsProps) {
  const { t } = useI18n();

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div>
        <Label>
          {t(
            labMode === "prep"
              ? "newRunPage.rawBundleInput"
              : labMode === "chunk"
                ? "newRunPage.cleanCorpusInput"
                : "newRunPage.chunksToSearch",
          )}
        </Label>
        {labMode === "prep" ? (
          <Select
            value={rawBundleId || rawBundles[0]?.id || ""}
            onChange={(event) => onRawBundleIdChange(event.target.value)}
            required
          >
            {rawBundles.map((artifact) => (
              <option key={artifact.id} value={artifact.id}>
                {artifactDisplayName(artifact.type, artifact.meta, artifact.id)}
              </option>
            ))}
          </Select>
        ) : labMode === "chunk" ? (
          <Select
            value={cleanCorpusId || cleanCorpora[0]?.id || ""}
            onChange={(event) => onCleanCorpusIdChange(event.target.value)}
            required
          >
            {cleanCorpora.map((artifact) => (
              <option key={artifact.id} value={artifact.id}>
                {artifactDisplayName(artifact.type, artifact.meta, artifact.id)}
              </option>
            ))}
          </Select>
        ) : (
          <Select
            value={chunkSetId || chunkSets[0]?.id || ""}
            onChange={(event) => onChunkSetIdChange(event.target.value)}
            required
          >
            {chunkSets.map((artifact) => (
              <option key={artifact.id} value={artifact.id}>
                {artifactLabel(artifact, "chunk", t)}
              </option>
            ))}
          </Select>
        )}
      </div>
      <div>
        <Label>{t("newRunPage.goldenTestSet")}</Label>
        <Select
          value={testSetId || testSets[0]?.id || ""}
          onChange={(event) => onTestSetIdChange(event.target.value)}
          required
        >
          {testSets.map((artifact) => (
            <option key={artifact.id} value={artifact.id}>
              {artifactLabel(artifact, "test", t)}
            </option>
          ))}
        </Select>
      </div>
    </div>
  );
}

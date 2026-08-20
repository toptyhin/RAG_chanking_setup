import { experimentReportUrl } from "@/lib/api";
import { Section } from "@/components/ui";
import { useI18n } from "@/lib/locale";

type RunResultsReportSectionProps = {
  runId: string;
  reportObjectKey?: string | null;
};

export function RunResultsReportSection({
  runId,
  reportObjectKey,
}: RunResultsReportSectionProps) {
  const { t } = useI18n();

  return (
    <Section title={t("runPage.reportTitle")} description={t("runPage.reportDescription")}>
      {reportObjectKey ? (
        <a
          className="text-sm font-medium text-[var(--accent)] underline"
          href={experimentReportUrl(runId)}
          target="_blank"
          rel="noreferrer"
        >
          {t("runPage.downloadReport")}
        </a>
      ) : (
        <p className="text-sm text-[var(--muted)]">{t("runPage.reportNotReady")}</p>
      )}
    </Section>
  );
}

"use client";

import { Button, ErrorBox } from "@/components/ui";
import { useI18n } from "@/lib/locale";

export default function ProjectError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { t } = useI18n();
  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold">{t("routeErrors.projectTitle")}</h1>
      <ErrorBox message={error.message || t("routeErrors.unknown")} />
      <Button type="button" className="mt-3" onClick={reset}>
        {t("routeErrors.retry")}
      </Button>
    </div>
  );
}

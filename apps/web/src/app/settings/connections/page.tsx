"use client";

import { useEffect, useState } from "react";
import { BackLink } from "@/components/back-link";
import { EmbeddingProviderForm } from "@/components/embedding-provider-form";
import { LlmProviderForm } from "@/components/llm-provider-form";
import { PromptEditorForm } from "@/components/prompt-editor-form";
import { RerankModelForm } from "@/components/rerank-model-form";
import { Callout, Section, TabBar } from "@/components/ui";
import { useI18n } from "@/lib/locale";
import { readReturnTo } from "@/lib/return-to";

type ConnectionTab = "embedding" | "questions" | "rerank" | "prompts";
const TABS: ConnectionTab[] = ["embedding", "questions", "rerank", "prompts"];

function readSearch(): URLSearchParams {
  if (typeof window === "undefined") return new URLSearchParams();
  return new URLSearchParams(window.location.search);
}

function readTab(): ConnectionTab {
  const tab = readSearch().get("tab");
  return tab && TABS.includes(tab as ConnectionTab) ? (tab as ConnectionTab) : "embedding";
}

function readBackHref(): string {
  return readReturnTo(readSearch(), "/projects");
}

export default function ConnectionsPage() {
  const { t } = useI18n();
  const [tab, setTabState] = useState<ConnectionTab>("embedding");
  const [backHref, setBackHref] = useState("/projects");

  useEffect(() => {
    setTabState(readTab());
    setBackHref(readBackHref());
    const sync = () => {
      setTabState(readTab());
      setBackHref(readBackHref());
    };
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);

  function setTab(next: ConnectionTab) {
    setTabState(next);
    const url = new URL(window.location.href);
    url.searchParams.set("tab", next);
    window.history.pushState(null, "", url.toString());
  }

  const tabs = [
    { id: "embedding" as const, label: t("connections.embedding"), description: t("connections.embeddingHint") },
    { id: "questions" as const, label: t("connections.questions"), description: t("connections.questionsHint") },
    { id: "rerank" as const, label: t("connections.rerank"), description: t("connections.rerankHint") },
    { id: "prompts" as const, label: t("connections.prompts"), description: t("connections.promptsHint") },
  ];

  return (
    <main>
      <div className="mb-2 flex items-center gap-2">
        <BackLink href={backHref} label={t("common.back")} />
        <h1 className="text-xl font-semibold leading-8">{t("connections.title")}</h1>
      </div>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[var(--muted)]">
        {t("connections.description")}
      </p>
      <Callout className="my-5">{t("connections.globalCallout")}</Callout>
      <TabBar tabs={tabs} value={tab} onChange={setTab} />

      {tab === "embedding" ? (
        <Section title={t("connections.embedding")} description={t("connections.embeddingDescription")}>
          <EmbeddingProviderForm />
        </Section>
      ) : null}
      {tab === "questions" ? (
        <Section title={t("connections.questions")} description={t("connections.questionsDescription")}>
          <LlmProviderForm />
        </Section>
      ) : null}
      {tab === "rerank" ? (
        <Section title={t("connections.rerank")} description={t("connections.rerankDescription")}>
          <RerankModelForm />
        </Section>
      ) : null}
      {tab === "prompts" ? (
        <Section title={t("connections.prompts")} description={t("connections.promptsDescription")}>
          <PromptEditorForm />
        </Section>
      ) : null}
    </main>
  );
}

import Link from "next/link";
import type { Artifact } from "@/lib/types";
import {
  buildArtifactLineage,
  type LineageNode,
} from "@/lib/lineage";
import { artifactDisplayName, artifactSummary } from "@/lib/format";
import { useI18n } from "@/lib/locale";

function hrefForNode(
  projectId: string,
  node: LineageNode,
): string | null {
  if (node.isCurrent) return null;
  if (node.kind === "experiment") {
    return `/projects/${projectId}/runs/${node.id}`;
  }
  if (node.kind === "artifact") {
    return `/projects/${projectId}/artifacts/${node.id}`;
  }
  return null;
}

function LineageChip({
  projectId,
  node,
}: {
  projectId: string;
  node: LineageNode;
}) {
  const { t } = useI18n();
  const summary = artifactSummary(node.meta, t);
  const href = hrefForNode(projectId, node);

  const name = artifactDisplayName(node.type, node.meta, node.id);
  const body = (
    <>
      <span className="font-medium text-[var(--fg)]">{name}</span>
      {summary ? (
        <span className="text-[var(--muted)]">{summary}</span>
      ) : null}
      {node.isCurrent ? (
        <span className="text-[var(--accent)]">
          {t("artifactDetail.lineageCurrent")}
        </span>
      ) : null}
    </>
  );

  const className = [
    "inline-flex max-w-full flex-col gap-0.5 rounded-md border px-3 py-2 text-xs",
    node.isCurrent
      ? "border-[var(--accent)] bg-[var(--accent-soft)]"
      : "border-[var(--border)] bg-[var(--bg)]/40",
    href ? "transition-colors hover:border-[var(--accent)]" : "",
  ].join(" ");

  if (href) {
    return (
      <Link href={href} className={className} title={node.id}>
        {body}
      </Link>
    );
  }

  return (
    <div className={className} title={node.id}>
      {body}
    </div>
  );
}

export function ArtifactLineageView({
  projectId,
  artifact,
  projectArtifacts,
}: {
  projectId: string;
  artifact: Artifact;
  projectArtifacts: Artifact[];
}) {
  const { t } = useI18n();
  const { chain, sideParents } = buildArtifactLineage(
    artifact,
    projectArtifacts,
  );

  if (chain.length <= 1 && sideParents.length === 0) {
    return (
      <p className="text-sm text-[var(--muted)]">
        {t("artifactDetail.lineageRoot")}
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <ol className="flex flex-wrap items-stretch gap-2">
        {chain.map((node, index) => (
          <li key={node.id} className="flex items-center gap-2">
            {index > 0 ? (
              <span
                aria-hidden
                className="select-none text-[var(--muted)]"
              >
                →
              </span>
            ) : null}
            <LineageChip projectId={projectId} node={node} />
          </li>
        ))}
      </ol>

      {sideParents.length > 0 ? (
        <div>
          <p className="mb-2 text-xs font-medium text-[var(--muted)]">
            {t("artifactDetail.lineageAlsoFrom")}
          </p>
          <ul className="flex flex-wrap gap-2">
            {sideParents.map((node) => (
              <li key={node.id}>
                <LineageChip projectId={projectId} node={node} />
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

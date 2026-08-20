import type { Artifact } from "./types";

export type LineageKind = "artifact" | "experiment" | "unknown";

export type LineageNode = {
  id: string;
  type: string;
  meta: Record<string, unknown>;
  kind: LineageKind;
  isCurrent: boolean;
};

export type ArtifactLineage = {
  /** Root → … → current (data pipeline). */
  chain: LineageNode[];
  /** Extra parents of the current artifact not on the main chain (e.g. experiment run). */
  sideParents: LineageNode[];
};

function nodeKind(id: string, artifact: Artifact | undefined): LineageKind {
  if (artifact) return "artifact";
  if (id.startsWith("run_")) return "experiment";
  return "unknown";
}

function resolveNode(
  id: string,
  byId: Map<string, Artifact>,
  isCurrent: boolean,
): LineageNode {
  const artifact = byId.get(id);
  const kind = nodeKind(id, artifact);
  return {
    id,
    type:
      artifact?.type ??
      (kind === "experiment" ? "experiment_run" : "unknown"),
    meta: artifact?.meta ?? {},
    kind,
    isCurrent,
  };
}

function isExperimentParent(
  id: string,
  byId: Map<string, Artifact>,
): boolean {
  if (id.startsWith("run_")) return true;
  return byId.get(id)?.type === "experiment_run";
}

/** Prefer a data-pipeline parent over an experiment run when walking ancestry. */
function pickContinuation(
  parentIds: string[],
  byId: Map<string, Artifact>,
): string | null {
  if (parentIds.length === 0) return null;
  const data = parentIds.find((id) => !isExperimentParent(id, byId));
  return data ?? parentIds[0] ?? null;
}

/**
 * Build a root→current generation chain by walking parent_ids,
 * preferring non-experiment parents so the pipeline stays readable.
 */
export function buildArtifactLineage(
  artifact: Artifact,
  projectArtifacts: Artifact[],
): ArtifactLineage {
  const byId = new Map(projectArtifacts.map((a) => [a.id, a]));
  byId.set(artifact.id, artifact);

  const chain: LineageNode[] = [];
  const visited = new Set<string>();
  let current: Artifact | undefined = artifact;

  while (current && !visited.has(current.id)) {
    visited.add(current.id);
    chain.unshift(
      resolveNode(current.id, byId, current.id === artifact.id),
    );

    const nextId = pickContinuation(current.parent_ids, byId);
    if (!nextId || visited.has(nextId)) break;

    const nextArtifact = byId.get(nextId);
    if (!nextArtifact) {
      chain.unshift(resolveNode(nextId, byId, false));
      break;
    }
    current = nextArtifact;
  }

  const chainIds = new Set(chain.map((n) => n.id));
  const sideParents = artifact.parent_ids.reduce<LineageNode[]>((acc, id) => {
    if (!chainIds.has(id)) {
      acc.push(resolveNode(id, byId, false));
    }
    return acc;
  }, []);

  return { chain, sideParents };
}

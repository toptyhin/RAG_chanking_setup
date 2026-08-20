import type {
  Artifact,
  CachedModel,
  ChunkPreview,
  ChunkSetContent,
  EmbeddingConfig,
  EmbeddingConfigUpdate,
  EmbeddingConnectionTest,
  EmbeddingModelsList,
  EvidenceCandidatesResult,
  Experiment,
  ExperimentProgressEvent,
  HubModel,
  LlmConfig,
  LlmConfigUpdate,
  LlmConnectionTest,
  LlmModelsList,
  LoadedEmbedding,
  LoadedRerank,
  ModelLoadJob,
  ModelStorageItem,
  Project,
  PromptTemplate,
  PreparedQuestionsResult,
  PrepareEstimate,
  SavePromptVersion,
  TestSetContent,
} from "./types";

function apiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return base.replace(/\/$/, "");
}

export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${apiBase()}${p}`;
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
    return JSON.stringify(data.detail ?? data);
  } catch {
    return res.statusText || `HTTP ${res.status}`;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), init);
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export function listProjects(): Promise<Project[]> {
  return request("/projects");
}

export function createProject(body: {
  name: string;
  description?: string | null;
}): Promise<Project> {
  return request("/projects", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getProject(projectId: string): Promise<Project> {
  return request(`/projects/${projectId}`);
}

export function listArtifacts(
  projectId: string,
  type?: string,
): Promise<Artifact[]> {
  const qs = type ? `?type=${encodeURIComponent(type)}` : "";
  return request(`/projects/${projectId}/artifacts${qs}`);
}

export function deleteArtifact(
  artifactId: string,
  options?: { cascade?: boolean },
): Promise<{ deleted: string[] }> {
  const qs = options?.cascade ? "?cascade=true" : "";
  return request(`/artifacts/${artifactId}${qs}`, { method: "DELETE" });
}

export async function uploadRawBundle(
  projectId: string,
  files: FileList | File[],
): Promise<{
  artifact: Artifact;
  files_stored: number;
  clean_corpus: Artifact;
  document_count: number;
  prep_metrics: Record<string, unknown>;
}> {
  const form = new FormData();
  for (const file of Array.from(files)) {
    form.append("files", file);
  }
  return request(`/projects/${projectId}/raw-bundles`, {
    method: "POST",
    body: form,
  });
}

export type ChunkerProviderId =
  | "semchunk"
  | "chunklet"
  | "reference_fixed";

export type ChunkerProviderInfo = {
  id: ChunkerProviderId;
  label: string;
  modes: string[];
  available: boolean;
  options_schema: Record<string, unknown>;
  unavailable_reason: string | null;
};

export type CreateChunkSetBody = {
  clean_corpus_id: string;
  provider: ChunkerProviderId;
  [key: string]: unknown;
};

export function listChunkers(): Promise<ChunkerProviderInfo[]> {
  return request("/chunkers");
}

export function createChunkSet(
  projectId: string,
  body: CreateChunkSetBody,
): Promise<{ artifact: Artifact; chunk_count: number }> {
  return request(`/projects/${projectId}/chunk-sets`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function previewChunkSet(
  projectId: string,
  body: CreateChunkSetBody & { preview_count?: number },
): Promise<ChunkPreview> {
  return request(`/projects/${projectId}/chunk-sets/preview`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function importByoChunks(
  projectId: string,
  body: unknown,
): Promise<{ artifact: Artifact; chunk_count: number }> {
  return request(`/projects/${projectId}/chunk-sets/import`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function importTestSet(
  projectId: string,
  body: unknown,
): Promise<{
  artifact: Artifact;
  query_count: number;
  source: string;
  reviewed: boolean;
  reviewed_count: number;
  source_counts: Record<string, number>;
}> {
  return request(`/projects/${projectId}/test-sets/import`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function prepareTestSetQuestions(
  projectId: string,
  body: {
    clean_corpus_id: string;
    chunk_set_id?: string;
    prompt_id?: string;
  },
): Promise<PreparedQuestionsResult> {
  return request(`/projects/${projectId}/test-sets/prepare`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function estimatePrepareQuestions(
  projectId: string,
  body: { clean_corpus_id: string; prompt_id?: string },
): Promise<PrepareEstimate> {
  return request(`/projects/${projectId}/test-sets/prepare-estimate`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function importArtifactsFromProject(
  projectId: string,
  body: {
    source_project_id: string;
    artifact_ids: string[];
    include_parents?: boolean;
  },
): Promise<{ artifacts: Artifact[]; id_map: Record<string, string> }> {
  return request(`/projects/${projectId}/artifacts/import`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function createExperiment(body: {
  project_id: string;
  evaluates?: "retrieval" | "prep" | "chunk";
  chunk_set_id?: string;
  raw_bundle_id?: string;
  clean_corpus_id?: string;
  test_set_id: string;
  fixed?: Record<string, unknown>;
  swept?: Record<string, unknown[]>;
  disclaimer?: string | null;
}): Promise<Experiment> {
  return request("/experiments", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ evaluates: "retrieval", ...body }),
  });
}

export function listExperiments(projectId: string): Promise<Experiment[]> {
  return request(`/projects/${projectId}/experiments`);
}

export function getExperiment(runId: string): Promise<Experiment> {
  return request(`/experiments/${runId}`);
}

export function subscribeExperimentProgress(
  runId: string,
  onEvent: (progress: ExperimentProgressEvent, event: string) => void,
): () => void {
  const source = new EventSource(apiUrl(`/experiments/${runId}/progress`));
  let closed = false;
  const close = () => {
    if (closed) return;
    closed = true;
    source.close();
  };
  const handle = (eventName: string) => (event: MessageEvent) => {
    try {
      const progress = JSON.parse(String(event.data)) as ExperimentProgressEvent;
      onEvent(progress, eventName);
      if (
        eventName === "done" ||
        eventName === "error" ||
        progress.status === "completed" ||
        progress.status === "failed"
      ) {
        close();
      }
    } catch {
      /* ignore malformed events */
    }
  };
  source.addEventListener("progress", handle("progress"));
  source.addEventListener("done", handle("done"));
  source.addEventListener("error", (event) => {
    if (event instanceof MessageEvent && event.data) {
      handle("error")(event);
    }
  });
  return close;
}

export function getArtifact(artifactId: string): Promise<Artifact> {
  return request(`/artifacts/${artifactId}`);
}

export function getArtifactContent<T = unknown>(
  artifactId: string,
): Promise<T> {
  return request(`/artifacts/${artifactId}/content`);
}

export function getChunkSetContent(
  chunkSetId: string,
): Promise<ChunkSetContent> {
  return getArtifactContent<ChunkSetContent>(chunkSetId);
}

export function getTestSetContent(testSetId: string): Promise<TestSetContent> {
  return getArtifactContent<TestSetContent>(testSetId);
}

export function fetchEvidenceCandidates(
  projectId: string,
  body: {
    chunk_set_id: string;
    clean_corpus_id?: string;
    question: string;
    expected_answer?: string;
    source_quote?: string;
    evidence_quotes?: string[];
    query_type?: string;
    limit?: number;
  },
): Promise<EvidenceCandidatesResult> {
  return request(`/projects/${projectId}/test-sets/evidence-candidates`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function experimentReportUrl(runId: string): string {
  return apiUrl(`/experiments/${runId}/report`);
}

export function searchEmbeddingModels(
  q: string,
  limit = 20,
): Promise<{ items: HubModel[] }> {
  const qs = new URLSearchParams({ q, limit: String(limit) });
  return request(`/models/embedding/search?${qs}`);
}

export function searchRerankModels(
  q: string,
  limit = 20,
): Promise<{ items: HubModel[] }> {
  const qs = new URLSearchParams({ q, limit: String(limit) });
  return request(`/models/rerank/search?${qs}`);
}

export function fetchModelStorageSizes(
  modelIds: string[],
): Promise<{ items: ModelStorageItem[] }> {
  return request("/models/storage", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ model_ids: modelIds }),
  });
}

export function getCurrentEmbedding(): Promise<{
  model_id: string;
  dimension: number;
  default_model: string;
}> {
  return request("/models/embedding/current");
}

export function setCurrentEmbedding(modelId: string): Promise<{
  model_id: string;
  dimension: number;
  default_model: string;
}> {
  return request("/models/embedding/current", {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ model_id: modelId }),
  });
}

export function getCurrentRerank(): Promise<{
  model_id: string;
  default_model: string;
}> {
  return request("/models/rerank/current");
}

export function setCurrentRerank(modelId: string): Promise<{
  model_id: string;
  default_model: string;
}> {
  return request("/models/rerank/current", {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ model_id: modelId }),
  });
}

export function listLoadedEmbeddings(): Promise<LoadedEmbedding[]> {
  return request("/models/embedding/loaded");
}

export function listLoadedReranks(): Promise<LoadedRerank[]> {
  return request("/models/rerank/loaded");
}

export function listCachedEmbeddings(
  q = "",
): Promise<CachedModel[]> {
  const qs = new URLSearchParams({ q });
  return request(`/models/embedding/cached?${qs}`);
}

export function listCachedReranks(q = ""): Promise<CachedModel[]> {
  const qs = new URLSearchParams({ q });
  return request(`/models/rerank/cached?${qs}`);
}

export function loadEmbeddingModel(modelId: string): Promise<ModelLoadJob> {
  return request("/models/embedding/load", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ model_id: modelId }),
  });
}

export function loadRerankModel(modelId: string): Promise<ModelLoadJob> {
  return request("/models/rerank/load", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ model_id: modelId }),
  });
}

export function subscribeModelJobProgress(
  jobId: string,
  onEvent: (job: ModelLoadJob, event: string) => void,
): () => void {
  const source = new EventSource(apiUrl(`/models/jobs/${jobId}/progress`));
  let closed = false;

  const close = () => {
    if (closed) return;
    closed = true;
    source.close();
  };

  const isTerminal = (job: ModelLoadJob, eventName: string) =>
    eventName === "done" ||
    eventName === "error" ||
    job.stage === "ready" ||
    job.stage === "failed";

  const handle = (eventName: string) => (ev: MessageEvent) => {
    try {
      const data = JSON.parse(String(ev.data)) as ModelLoadJob;
      onEvent(data, eventName);
      if (isTerminal(data, eventName)) {
        close();
      }
    } catch {
      /* ignore malformed */
    }
  };

  source.addEventListener("progress", handle("progress"));
  source.addEventListener("done", handle("done"));
  source.addEventListener("error", (ev) => {
    // Named SSE "error" event with payload vs transport/reconnect error.
    if (ev instanceof MessageEvent && typeof ev.data === "string" && ev.data) {
      handle("error")(ev);
      return;
    }
    // Stream ended or network blip — stop auto-reconnect loop.
    close();
  });

  return close;
}

export function getLlmConfig(): Promise<LlmConfig> {
  return request("/llm/config");
}

export function updateLlmConfig(body: LlmConfigUpdate): Promise<LlmConfig> {
  return request("/llm/config", {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function testLlmConnection(
  body?: LlmConfigUpdate,
): Promise<LlmConnectionTest> {
  return request("/llm/test", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
}

export function listLlmModels(body?: LlmConfigUpdate): Promise<LlmModelsList> {
  return request("/llm/models", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
}

export function getEmbeddingConfig(): Promise<EmbeddingConfig> {
  return request("/embedding/config");
}

export function updateEmbeddingConfig(
  body: EmbeddingConfigUpdate,
): Promise<EmbeddingConfig> {
  return request("/embedding/config", {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function testEmbeddingConnection(
  body?: EmbeddingConfigUpdate,
): Promise<EmbeddingConnectionTest> {
  return request("/embedding/test", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
}

export function listEmbeddingProviderModels(
  body?: EmbeddingConfigUpdate,
): Promise<EmbeddingModelsList> {
  return request("/embedding/models", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
}

export function getPrompt(promptId: string): Promise<PromptTemplate> {
  return request(`/prompts/${encodeURIComponent(promptId)}`);
}

export function savePromptVersion(
  promptId: string,
  body: SavePromptVersion,
): Promise<PromptTemplate> {
  return request(`/prompts/${encodeURIComponent(promptId)}/versions`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function setActivePromptVersion(
  promptId: string,
  version: number,
): Promise<PromptTemplate> {
  return request(`/prompts/${encodeURIComponent(promptId)}/active`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ version }),
  });
}

export function resetPrompt(promptId: string): Promise<PromptTemplate> {
  return request(`/prompts/${encodeURIComponent(promptId)}/reset`, {
    method: "POST",
  });
}


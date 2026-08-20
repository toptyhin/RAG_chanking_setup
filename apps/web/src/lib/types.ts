export type Project = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};

export type Artifact = {
  id: string;
  project_id: string;
  type: string;
  parent_ids: string[];
  content_hash: string | null;
  object_key: string | null;
  meta: Record<string, unknown>;
  created_at: string;
};

export type MetricsRow = {
  id: number;
  point_index: number;
  config: Record<string, unknown>;
  metrics: Record<string, unknown>;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  index_run_id: string | null;
};

export type Progress = {
  done: number;
  total: number;
  percent: number;
  current_config: Record<string, unknown> | null;
};

export type ParetoPoint = {
  point_index: number;
  recall: number;
  latency_p95_ms: number;
  index_size_mb: number;
  config: Record<string, unknown>;
  metrics?: Record<string, unknown>;
};

export type Experiment = {
  id: string;
  project_id: string;
  evaluates: string;
  start_artifact_type: string;
  start_artifact_id: string;
  test_set_id: string | null;
  fixed: Record<string, unknown>;
  swept: Record<string, unknown[]>;
  status: string;
  disclaimer: string | null;
  error: string | null;
  meta: Record<string, unknown>;
  progress: Progress | null;
  pareto: ParetoPoint[];
  report_object_key: string | null;
  metrics_rows: MetricsRow[];
};

export type ExperimentProgressEvent = {
  run_id: string;
  status: string;
  done: number;
  total: number;
  percent: number;
  current_config: Record<string, unknown> | null;
  error?: string;
};

export type ChunkContent = {
  chunk_id: string;
  doc_id: string;
  text: string;
  start_char?: number | null;
  end_char?: number | null;
};

export type ChunkSetContent = {
  id: string;
  chunks: ChunkContent[];
};

export type ChunkPreview = {
  chunk_count: number;
  document_count: number;
  total_chars: number;
  size: {
    min_chars: number;
    p50_chars: number;
    p95_chars: number;
    max_chars: number;
    average_chars: number;
    min_tokens: number;
    p50_tokens: number;
    p95_tokens: number;
    max_tokens: number;
    average_tokens: number;
    tokens_note?: string | null;
  };
  samples: Array<ChunkContent & { size_chars: number; size_tokens: number }>;
  persisted: false;
};

export type RawFileRef = {
  path: string;
  original_name: string;
  content_type?: string | null;
  size_bytes?: number | null;
  sha256?: string | null;
};

export type RawBundleContent = {
  id: string;
  files: RawFileRef[];
  meta?: Record<string, unknown>;
};

export type CleanDocument = {
  doc_id: string;
  text: string;
  source_path?: string | null;
  page?: number | null;
  language?: string | null;
};

export type CleanCorpusContent = {
  id: string;
  documents: CleanDocument[];
  prep_pipeline_id?: string | null;
  meta?: Record<string, unknown>;
};

export type RelevantSpan = {
  doc_id: string;
  start: number;
  end: number;
};

export type TestQueryContent = {
  query_id: string;
  text: string;
  relevant_chunk_ids: string[];
  relevant_doc_ids?: string[];
  relevant_spans?: RelevantSpan[];
  relevance_grades?: Record<string, number>;
  expected_answer?: string | null;
  source_quote?: string | null;
  query_type?: string | null;
  source?: "synthetic" | "manual" | "imported" | "unknown";
  reviewed?: boolean;
  label_status?: string | null;
  meta?: Record<string, unknown>;
};

export type TestSetContent = {
  id: string;
  queries: TestQueryContent[];
  parent_ids?: string[];
  source?: "synthetic" | "manual" | "imported" | "mixed" | "unknown";
  reviewed?: boolean;
  meta?: Record<string, unknown>;
};

export type HubModel = {
  id: string;
  downloads: number;
  likes: number;
  pipeline_tag: string | null;
  tags: string[];
  library_name: string | null;
};

export type ModelStorageItem = {
  model_id: string;
  size_bytes: number | null;
};

export type ModelLoadJob = {
  job_id: string;
  model_id: string;
  status: string;
  stage: string;
  percent: number;
  message: string;
  error?: string | null;
  kind?: string;
};

export type LoadedEmbedding = {
  model_id: string;
  dimension: number;
  current: boolean;
};

export type LoadedRerank = {
  model_id: string;
  current?: boolean;
};

export type CachedModel = {
  model_id: string;
  size_bytes: number | null;
  in_memory: boolean;
};

export type TextLlmProvider = "ollama" | "openrouter" | "gigachat";

export type EmbeddingProviderKind =
  | "ollama"
  | "sentence_transformers"
  | "openrouter"
  | "gigachat";

export type LlmConfig = {
  provider: TextLlmProvider;
  ollama: {
    base_url: string;
    model: string;
  };
  openrouter: {
    base_url: string;
    model: string;
    api_key_configured: boolean;
    api_key_masked: string | null;
  };
  gigachat: {
    scope: string;
    base_url: string;
    auth_url: string;
    model: string;
    verify_ssl: boolean;
    credentials_configured: boolean;
    credentials_masked: string | null;
  };
};

export type ModelListPurpose = "text" | "embeddings" | "rerank";

export type LlmConfigUpdate = {
  provider?: TextLlmProvider;
  ollama?: {
    base_url?: string;
    model?: string;
  };
  openrouter?: {
    base_url?: string;
    api_key?: string;
    model?: string;
  };
  gigachat?: {
    credentials?: string;
    scope?: string;
    base_url?: string;
    auth_url?: string;
    model?: string;
    verify_ssl?: boolean;
  };
  /** Only used by /llm/models — filters catalog by modality. */
  purpose?: ModelListPurpose;
};

export type LlmConnectionTest = {
  ok: boolean;
  latency_ms: number;
  message: string;
  provider: TextLlmProvider;
  model: string | null;
  models: string[];
};

export type RemoteModelInfo = {
  id: string;
  name: string;
  context_length: number | null;
  modality: string | null;
  input_modalities: string[];
  output_modalities: string[];
  supported_parameters?: string[];
  /** Native / default embedding size when known. */
  dimension?: number | null;
  /** MRL (Matryoshka) sizes when the model supports multiple dims. */
  dimensions?: number[];
};

export type LlmModelsList = {
  ok: boolean;
  provider: TextLlmProvider;
  models: string[];
  items: RemoteModelInfo[];
  message: string | null;
};

export type EmbeddingModelsList = {
  ok: boolean;
  provider: EmbeddingProviderKind;
  models: string[];
  items: RemoteModelInfo[];
  message: string | null;
};

export type EmbeddingConfig = {
  provider: EmbeddingProviderKind;
  sentence_transformers: {
    model: string;
  };
  ollama: {
    base_url: string;
    model: string;
  };
  openrouter: {
    base_url: string;
    model: string;
    api_key_configured: boolean;
    api_key_masked: string | null;
  };
  gigachat: {
    scope: string;
    base_url: string;
    auth_url: string;
    model: string;
    verify_ssl: boolean;
    credentials_configured: boolean;
    credentials_masked: string | null;
  };
};

export type EmbeddingConfigUpdate = {
  provider?: EmbeddingProviderKind;
  sentence_transformers?: {
    model?: string;
  };
  ollama?: {
    base_url?: string;
    model?: string;
  };
  openrouter?: {
    base_url?: string;
    api_key?: string;
    model?: string;
  };
  gigachat?: {
    credentials?: string;
    scope?: string;
    base_url?: string;
    auth_url?: string;
    model?: string;
    verify_ssl?: boolean;
  };
};

export type EmbeddingConnectionTest = {
  ok: boolean;
  latency_ms: number;
  message: string;
  provider: EmbeddingProviderKind;
  model: string | null;
  models: string[];
};

export type PromptVersion = {
  version: number;
  body: string;
  created_at: string;
  note: string | null;
};

export type PromptTemplate = {
  id: string;
  name: string;
  description: string;
  active_version: number;
  active_body: string;
  document_placeholder: string;
  schema_placeholder: string;
  response_schema: Record<string, unknown>;
  versions: PromptVersion[];
};

export type PromptList = {
  prompts: PromptTemplate[];
};

export type SavePromptVersion = {
  body: string;
  note?: string;
  activate?: boolean;
  response_schema?: Record<string, unknown>;
};

export type PreparedQuestion = {
  text: string;
  relevant_chunk_ids: string[];
  relevant_spans?: RelevantSpan[];
  evidence_quotes?: string[];
  expected_answer: string | null;
  source_quote: string | null;
  level: string | null;
  query_type?: string | null;
};

export type EvidenceCandidate = {
  chunk_id: string;
  doc_id: string;
  text: string;
  start_char: number | null;
  end_char: number | null;
  score: number;
  reason: "quote" | "bm25" | "neighbor" | string;
};

export type EvidenceCandidatesResult = {
  candidates: EvidenceCandidate[];
  quote_spans: RelevantSpan[];
};

export type PreparedQuestionsResult = {
  questions: PreparedQuestion[];
  provider: TextLlmProvider;
  model: string;
  prompt_id: string;
  prompt_version: number;
  clean_corpus_id: string;
  document_count: number;
  document_chars: number;
  corpus_tokens_est: number;
  prompt_tokens_est: number;
  context_length: number | null;
  chunk_set_id: string | null;
  chunk_count: number;
  part_count?: number;
};

export type PrepareEstimate = {
  provider: TextLlmProvider;
  model: string;
  context_length: number | null;
  context_source: string | null;
  clean_corpus_id: string;
  document_count: number;
  corpus_chars: number;
  corpus_tokens_est: number;
  prompt_chars: number;
  prompt_tokens_est: number;
  fits_context: boolean | null;
  fits_single_pass?: boolean | null;
  part_count?: number;
  token_estimate_note: string;
};

export type IndexRunContent = {
  id: string;
  chunk_set_id: string;
  collection_name: string;
  embedding_model: string;
  dimension: number;
  quantization?: Record<string, unknown> | null;
  hnsw?: Record<string, unknown>;
  build_time_sec?: number | null;
  meta?: Record<string, unknown>;
};

export type SemchunkFormState = {
  chunk_size: number;
  overlap: number | null;
  token_counter: string;
};

export type ChunkletFormState = {
  mode: "document" | "code";
  lang: string;
  max_tokens: number | null;
  max_sentences: number | null;
  max_section_breaks: number | null;
  max_lines: number | null;
  max_functions: number | null;
  overlap_percent: number;
  offset: number;
  include_comments: boolean;
  docstring_mode: "summary" | "all" | "excluded";
  strict: boolean;
  token_counter: string;
};

export type ReferenceFormState = {
  size: number;
  overlap: number;
};

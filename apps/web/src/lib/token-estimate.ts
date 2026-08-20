/**
 * Conservative token estimate without a tokenizer.
 * Matches Python `rageval_llm_providers.limits.estimate_tokens`:
 * ASCII ≈ 4 chars/token; non-ASCII (e.g. Cyrillic) ≈ 2 chars/token.
 */
export function estimateTokens(text: string): number {
  const n = text?.length ?? 0;
  if (n <= 0) return 0;
  let ascii = 0;
  for (let i = 0; i < n; i += 1) {
    if ((text.charCodeAt(i) ?? 0) < 128) ascii += 1;
  }
  const other = n - ascii;
  return Math.max(1, Math.ceil(ascii / 4 + other / 2));
}

export function sizeFromText(text: string): { chars: number; tokens: number } {
  return { chars: text.length, tokens: estimateTokens(text) };
}

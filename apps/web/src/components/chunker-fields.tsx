"use client";

import { useState } from "react";
import { Input, Label, Select } from "@/components/ui";
import type { TranslationKey } from "@/i18n";
import { useI18n } from "@/lib/locale";
import type {
  ChunkletFormState,
  ReferenceFormState,
  SemchunkFormState,
} from "@/components/chunker-form-types";

type SemchunkField = "chunk_size" | "overlap" | "token_counter";

const SEMCHUNK_FIELD_HELP: Record<SemchunkField, TranslationKey> = {
  chunk_size: "chunkerForm.chunkSizeHelp",
  overlap: "chunkerForm.overlapHelp",
  token_counter: "chunkerForm.tokenCounterHelp",
};

type ChunkletField =
  | "mode"
  | "lang"
  | "token_counter"
  | "max_tokens"
  | "max_sentences"
  | "max_section_breaks"
  | "max_lines"
  | "max_functions"
  | "overlap_percent"
  | "docstring_mode"
  | "include_comments"
  | "strict";

const CHUNKLET_FIELD_HELP: Record<ChunkletField, TranslationKey> = {
  mode: "chunkerForm.modeHelp",
  lang: "chunkerForm.langHelp",
  token_counter: "chunkerForm.tokenCounterHelp",
  max_tokens: "chunkerForm.maxTokensHelp",
  max_sentences: "chunkerForm.maxSentencesHelp",
  max_section_breaks: "chunkerForm.maxSectionBreaksHelp",
  max_lines: "chunkerForm.maxLinesHelp",
  max_functions: "chunkerForm.maxFunctionsHelp",
  overlap_percent: "chunkerForm.overlapPercentHelp",
  docstring_mode: "chunkerForm.docstringModeHelp",
  include_comments: "chunkerForm.includeCommentsHelp",
  strict: "chunkerForm.strictHelp",
};

export function SemchunkFields({
  value,
  onChange,
}: {
  value: SemchunkFormState;
  onChange: (v: SemchunkFormState) => void;
}) {
  const { t } = useI18n();
  const [focused, setFocused] = useState<SemchunkField | null>(null);

  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <Label>{t("chunkerForm.chunkSize")}</Label>
          <Input
            type="number"
            min={1}
            value={value.chunk_size}
            onFocus={() => setFocused("chunk_size")}
            onChange={(e) =>
              onChange({ ...value, chunk_size: Number(e.target.value) })
            }
          />
        </div>
        <div>
          <Label>{t("chunkerForm.overlapOptional")}</Label>
          <Input
            type="number"
            min={0}
            step="any"
            value={value.overlap ?? ""}
            placeholder={t("chunkerForm.overlapPlaceholder")}
            onFocus={() => setFocused("overlap")}
            onChange={(e) =>
              onChange({
                ...value,
                overlap: e.target.value === "" ? null : Number(e.target.value),
              })
            }
          />
        </div>
        <div>
          <Label>{t("chunkerForm.tokenCounter")}</Label>
          <Select
            value={value.token_counter}
            onFocus={() => setFocused("token_counter")}
            onChange={(e) => {
              setFocused("token_counter");
              onChange({ ...value, token_counter: e.target.value });
            }}
          >
            <option value="words">{t("chunkerForm.tokenWords")}</option>
            <option value="chars">{t("chunkerForm.tokenChars")}</option>
            <option value="tiktoken:cl100k_base">tiktoken:cl100k_base</option>
          </Select>
        </div>
      </div>
      {focused ? (
        <p
          role="note"
          className="rounded-md border border-[var(--border)] bg-[var(--bg)]/50 px-3 py-2 text-xs text-[var(--muted)]"
        >
          {t(SEMCHUNK_FIELD_HELP[focused])}
        </p>
      ) : null}
    </div>
  );
}

export function ChunkletFields({
  value,
  onChange,
}: {
  value: ChunkletFormState;
  onChange: (v: ChunkletFormState) => void;
}) {
  const { t } = useI18n();
  const [focused, setFocused] = useState<ChunkletField | null>(null);

  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <Label>{t("chunkerForm.mode")}</Label>
          <Select
            value={value.mode}
            onFocus={() => setFocused("mode")}
            onChange={(e) => {
              const mode = e.target.value as "document" | "code";
              setFocused("mode");
              onChange({
                ...value,
                mode,
                ...(mode === "code"
                  ? { max_functions: value.max_functions ?? 1, max_sentences: null }
                  : { max_sentences: value.max_sentences ?? 5 }),
              });
            }}
          >
            <option value="document">{t("chunkerForm.modeDocument")}</option>
            <option value="code">{t("chunkerForm.modeCode")}</option>
          </Select>
        </div>
        {value.mode === "document" ? (
          <div>
            <Label>{t("chunkerForm.lang")}</Label>
            <Select
              value={value.lang}
              onFocus={() => setFocused("lang")}
              onChange={(e) => {
                setFocused("lang");
                onChange({ ...value, lang: e.target.value });
              }}
            >
              <option value="auto">auto</option>
              <option value="ru">ru</option>
              <option value="en">en</option>
            </Select>
          </div>
        ) : null}
        <div>
          <Label>{t("chunkerForm.tokenCounter")}</Label>
          <Select
            value={value.token_counter}
            onFocus={() => setFocused("token_counter")}
            onChange={(e) => {
              setFocused("token_counter");
              onChange({ ...value, token_counter: e.target.value });
            }}
          >
            <option value="words">{t("chunkerForm.tokenWords")}</option>
            <option value="chars">{t("chunkerForm.tokenChars")}</option>
            <option value="tiktoken:cl100k_base">tiktoken:cl100k_base</option>
          </Select>
        </div>
      </div>

      {value.mode === "document" ? (
        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <Label>{t("chunkerForm.maxTokens")}</Label>
            <Input
              type="number"
              min={12}
              value={value.max_tokens ?? ""}
              onFocus={() => setFocused("max_tokens")}
              onChange={(e) =>
                onChange({
                  ...value,
                  max_tokens: e.target.value === "" ? null : Number(e.target.value),
                })
              }
            />
          </div>
          <div>
            <Label>{t("chunkerForm.maxSentences")}</Label>
            <Input
              type="number"
              min={1}
              value={value.max_sentences ?? ""}
              onFocus={() => setFocused("max_sentences")}
              onChange={(e) =>
                onChange({
                  ...value,
                  max_sentences:
                    e.target.value === "" ? null : Number(e.target.value),
                })
              }
            />
          </div>
          <div>
            <Label>{t("chunkerForm.maxSectionBreaks")}</Label>
            <Input
              type="number"
              min={1}
              value={value.max_section_breaks ?? ""}
              onFocus={() => setFocused("max_section_breaks")}
              onChange={(e) =>
                onChange({
                  ...value,
                  max_section_breaks:
                    e.target.value === "" ? null : Number(e.target.value),
                })
              }
            />
          </div>
          <div>
            <Label>{t("chunkerForm.overlapPercent")}</Label>
            <Input
              type="number"
              min={0}
              max={75}
              value={value.overlap_percent}
              onFocus={() => setFocused("overlap_percent")}
              onChange={(e) =>
                onChange({ ...value, overlap_percent: Number(e.target.value) })
              }
            />
          </div>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <Label>{t("chunkerForm.maxTokens")}</Label>
            <Input
              type="number"
              min={12}
              value={value.max_tokens ?? ""}
              onFocus={() => setFocused("max_tokens")}
              onChange={(e) =>
                onChange({
                  ...value,
                  max_tokens: e.target.value === "" ? null : Number(e.target.value),
                })
              }
            />
          </div>
          <div>
            <Label>{t("chunkerForm.maxLines")}</Label>
            <Input
              type="number"
              min={5}
              value={value.max_lines ?? ""}
              onFocus={() => setFocused("max_lines")}
              onChange={(e) =>
                onChange({
                  ...value,
                  max_lines: e.target.value === "" ? null : Number(e.target.value),
                })
              }
            />
          </div>
          <div>
            <Label>{t("chunkerForm.maxFunctions")}</Label>
            <Input
              type="number"
              min={1}
              value={value.max_functions ?? ""}
              onFocus={() => setFocused("max_functions")}
              onChange={(e) =>
                onChange({
                  ...value,
                  max_functions:
                    e.target.value === "" ? null : Number(e.target.value),
                })
              }
            />
          </div>
          <div>
            <Label>{t("chunkerForm.docstringMode")}</Label>
            <Select
              value={value.docstring_mode}
              onFocus={() => setFocused("docstring_mode")}
              onChange={(e) => {
                setFocused("docstring_mode");
                onChange({
                  ...value,
                  docstring_mode: e.target
                    .value as ChunkletFormState["docstring_mode"],
                });
              }}
            >
              <option value="all">all</option>
              <option value="summary">summary</option>
              <option value="excluded">excluded</option>
            </Select>
          </div>
          <div className="flex items-end gap-4 pb-2 text-sm">
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={value.include_comments}
                onFocus={() => setFocused("include_comments")}
                onChange={(e) =>
                  onChange({ ...value, include_comments: e.target.checked })
                }
              />
              {t("chunkerForm.includeComments")}
            </label>
            <label className="inline-flex items-center gap-2">
              <input
                type="checkbox"
                checked={value.strict}
                onFocus={() => setFocused("strict")}
                onChange={(e) =>
                  onChange({ ...value, strict: e.target.checked })
                }
              />
              {t("chunkerForm.strict")}
            </label>
          </div>
        </div>
      )}
      {focused ? (
        <p
          role="note"
          className="rounded-md border border-[var(--border)] bg-[var(--bg)]/50 px-3 py-2 text-xs text-[var(--muted)]"
        >
          {t(CHUNKLET_FIELD_HELP[focused])}
        </p>
      ) : (
        <p className="text-xs text-[var(--muted)]">{t("chunkerForm.chunkletHint")}</p>
      )}
    </div>
  );
}

export function ReferenceFields({
  value,
  onChange,
}: {
  value: ReferenceFormState;
  onChange: (v: ReferenceFormState) => void;
}) {
  const { t } = useI18n();
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div>
        <Label>{t("projectPage.size")}</Label>
        <Input
          type="number"
          min={1}
          value={value.size}
          onChange={(e) => onChange({ ...value, size: Number(e.target.value) })}
        />
      </div>
      <div>
        <Label>{t("projectPage.overlap")}</Label>
        <Input
          type="number"
          min={0}
          value={value.overlap}
          onChange={(e) =>
            onChange({ ...value, overlap: Number(e.target.value) })
          }
        />
      </div>
      <p className="sm:col-span-2 text-xs text-[var(--muted)]">
        {t("chunkerForm.referenceHint")}
      </p>
    </div>
  );
}

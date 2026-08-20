"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useReducer } from "react";
import {
  getPrompt,
  resetPrompt,
  savePromptVersion,
  setActivePromptVersion,
} from "@/lib/api";
import { useI18n } from "@/lib/locale";
import type { PromptTemplate } from "@/lib/types";
import { Button, ErrorBox, Input, Label, Select, TextArea } from "@/components/ui";

const RAG_QUESTION_PREP_ID = "rag_question_prep";

function schemaToText(schema: Record<string, unknown> | undefined): string {
  return JSON.stringify(schema ?? {}, null, 2);
}

type EditorState = {
  body: string;
  schemaText: string;
  note: string;
  viewVersion: number | null;
  message: string | null;
  schemaError: string | null;
};

type EditorAction =
  | { type: "set_body"; body: string }
  | { type: "set_schema_text"; schemaText: string }
  | { type: "set_note"; note: string }
  | { type: "select_version"; version: number; body: string }
  | { type: "clear_schema_error" }
  | { type: "set_schema_error"; schemaError: string }
  | { type: "save_success"; data: PromptTemplate; message: string }
  | { type: "activate_success"; data: PromptTemplate; message: string }
  | { type: "reset_success"; data: PromptTemplate; message: string };

function initEditorState(data: PromptTemplate): EditorState {
  const active = data.versions.find((v) => v.version === data.active_version);
  return {
    body: active?.body ?? data.active_body,
    schemaText: schemaToText(data.response_schema),
    note: "",
    viewVersion: data.active_version,
    message: null,
    schemaError: null,
  };
}

function editorReducer(state: EditorState, action: EditorAction): EditorState {
  switch (action.type) {
    case "set_body":
      return { ...state, body: action.body };
    case "set_schema_text":
      return { ...state, schemaText: action.schemaText, schemaError: null };
    case "set_note":
      return { ...state, note: action.note };
    case "select_version":
      return {
        ...state,
        viewVersion: action.version,
        body: action.body,
        message: null,
      };
    case "clear_schema_error":
      return { ...state, schemaError: null };
    case "set_schema_error":
      return { ...state, schemaError: action.schemaError };
    case "save_success": {
      const active = action.data.versions.find(
        (v) => v.version === action.data.active_version,
      );
      return {
        ...state,
        viewVersion: action.data.active_version,
        body: active?.body ?? action.data.active_body,
        schemaText: schemaToText(action.data.response_schema),
        note: "",
        message: action.message,
        schemaError: null,
      };
    }
    case "activate_success":
      return { ...state, message: action.message };
    case "reset_success": {
      const active = action.data.versions.find(
        (v) => v.version === action.data.active_version,
      );
      return {
        body: active?.body ?? action.data.active_body,
        schemaText: schemaToText(action.data.response_schema),
        note: "",
        viewVersion: action.data.active_version,
        message: action.message,
        schemaError: null,
      };
    }
    default:
      return state;
  }
}

function promptEditorKey(data: PromptTemplate): string {
  return `${data.active_version}:${data.versions.length}:${schemaToText(data.response_schema)}`;
}

function PromptEditorLoaded({
  promptId,
  data,
}: {
  promptId: string;
  data: PromptTemplate;
}) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [state, dispatch] = useReducer(editorReducer, data, initEditorState);
  const { body, schemaText, note, viewVersion, message, schemaError } = state;

  const selectedMeta = useMemo(() => {
    if (viewVersion == null) return null;
    return data.versions.find((v) => v.version === viewVersion) ?? null;
  }, [data.versions, viewVersion]);

  const savedSchemaText = useMemo(
    () => schemaToText(data.response_schema),
    [data.response_schema],
  );

  const dirty = useMemo(() => {
    const bodyDirty = selectedMeta
      ? body !== selectedMeta.body
      : body.trim().length > 0;
    const schemaDirty = schemaText !== savedSchemaText;
    return bodyDirty || schemaDirty;
  }, [body, selectedMeta, schemaText, savedSchemaText]);

  const saveMut = useMutation({
    mutationFn: () => {
      let response_schema: Record<string, unknown>;
      try {
        const parsed: unknown = JSON.parse(schemaText);
        if (
          parsed === null ||
          typeof parsed !== "object" ||
          Array.isArray(parsed)
        ) {
          throw new Error(t("promptForm.schemaMustBeObject"));
        }
        response_schema = parsed as Record<string, unknown>;
        dispatch({ type: "clear_schema_error" });
      } catch (err) {
        const msg =
          err instanceof SyntaxError
            ? t("promptForm.schemaInvalidJson")
            : err instanceof Error
              ? err.message
              : t("promptForm.schemaInvalidJson");
        dispatch({ type: "set_schema_error", schemaError: msg });
        return Promise.reject(new Error(msg));
      }
      return savePromptVersion(promptId, {
        body,
        note: note.trim() || undefined,
        activate: true,
        response_schema,
      });
    },
    onSuccess: (saved) => {
      qc.setQueryData(["prompts", promptId], saved);
      dispatch({
        type: "save_success",
        data: saved,
        message: t("promptForm.saved", { version: saved.active_version }),
      });
    },
  });

  const activateMut = useMutation({
    mutationFn: (version: number) => setActivePromptVersion(promptId, version),
    onSuccess: (saved) => {
      qc.setQueryData(["prompts", promptId], saved);
      dispatch({
        type: "activate_success",
        data: saved,
        message: t("promptForm.activated", { version: saved.active_version }),
      });
    },
  });

  const resetMut = useMutation({
    mutationFn: () => resetPrompt(promptId),
    onSuccess: (saved) => {
      qc.setQueryData(["prompts", promptId], saved);
      dispatch({
        type: "reset_success",
        data: saved,
        message: t("promptForm.resetDone", { version: saved.active_version }),
      });
    },
  });

  function onSelectVersion(version: number) {
    const found = data.versions.find((v) => v.version === version);
    dispatch({
      type: "select_version",
      version,
      body: found?.body ?? body,
    });
  }

  const isActiveView = viewVersion === data.active_version;
  const busy = saveMut.isPending || activateMut.isPending || resetMut.isPending;

  return (
    <div className="grid gap-4">
      <p className="text-sm text-[var(--muted)]">{t("promptForm.hint")}</p>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <Label>{t("promptForm.version")}</Label>
          <Select
            value={viewVersion ?? data.active_version}
            onChange={(e) => onSelectVersion(Number(e.target.value))}
            disabled={busy}
          >
            {data.versions.map((v) => (
              <option key={v.version} value={v.version}>
                {t("promptForm.versionOption", {
                  version: v.version,
                  active:
                    v.version === data.active_version
                      ? t("promptForm.activeMark")
                      : "",
                  note: v.note ? ` — ${v.note}` : "",
                })}
              </option>
            ))}
          </Select>
          {selectedMeta ? (
            <p className="mt-1 text-xs text-[var(--muted)]">
              {t("promptForm.createdAt", { at: selectedMeta.created_at })}
            </p>
          ) : null}
        </div>
        <div>
          <Label>{t("promptForm.note")}</Label>
          <Input
            value={note}
            onChange={(e) => dispatch({ type: "set_note", note: e.target.value })}
            placeholder={t("promptForm.notePlaceholder")}
            disabled={busy}
          />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <Label>{t("promptForm.body")}</Label>
          <TextArea
            rows={18}
            value={body}
            onChange={(e) => dispatch({ type: "set_body", body: e.target.value })}
            disabled={busy}
            spellCheck={false}
            className="font-mono text-sm"
          />
          <p className="mt-1 text-xs text-[var(--muted)]">
            {t("promptForm.placeholderHint", {
              document: data.document_placeholder,
              schema: data.schema_placeholder,
            })}
          </p>
        </div>
        <div>
          <Label>{t("promptForm.schema")}</Label>
          <TextArea
            rows={18}
            value={schemaText}
            onChange={(e) =>
              dispatch({ type: "set_schema_text", schemaText: e.target.value })
            }
            disabled={busy}
            spellCheck={false}
            className="font-mono text-sm"
          />
          <p className="mt-1 text-xs text-[var(--muted)]">
            {t("promptForm.schemaHint")}
          </p>
          {schemaError ? (
            <p className="mt-1 text-xs text-red-600">{schemaError}</p>
          ) : null}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          disabled={busy || !body.trim() || !dirty}
          onClick={() => saveMut.mutate()}
        >
          {saveMut.isPending ? t("promptForm.saving") : t("promptForm.save")}
        </Button>
        <Button
          type="button"
          className="bg-transparent text-[var(--fg)] ring-1 ring-[var(--border)]"
          disabled={busy || isActiveView || viewVersion == null}
          onClick={() => {
            if (viewVersion != null) activateMut.mutate(viewVersion);
          }}
        >
          {activateMut.isPending
            ? t("promptForm.activating")
            : t("promptForm.activate")}
        </Button>
        <Button
          type="button"
          className="bg-transparent text-[var(--fg)] ring-1 ring-[var(--border)]"
          disabled={busy}
          onClick={() => {
            if (window.confirm(t("promptForm.resetConfirm"))) {
              resetMut.mutate();
            }
          }}
        >
          {resetMut.isPending ? t("promptForm.resetting") : t("promptForm.reset")}
        </Button>
        {dirty ? (
          <span className="text-xs text-[var(--muted)]">{t("promptForm.unsaved")}</span>
        ) : null}
        {isActiveView && !dirty ? (
          <span className="text-xs text-[var(--muted)]">
            {t("promptForm.activeNow", { version: data.active_version })}
          </span>
        ) : null}
      </div>

      {message ? (
        <p className="text-sm text-[var(--muted)]">{message}</p>
      ) : null}
      {saveMut.isError ? (
        <ErrorBox
          message={
            saveMut.error instanceof Error
              ? saveMut.error.message
              : t("promptForm.saveFailed")
          }
        />
      ) : null}
      {activateMut.isError ? (
        <ErrorBox
          message={
            activateMut.error instanceof Error
              ? activateMut.error.message
              : t("promptForm.activateFailed")
          }
        />
      ) : null}
      {resetMut.isError ? (
        <ErrorBox
          message={
            resetMut.error instanceof Error
              ? resetMut.error.message
              : t("promptForm.resetFailed")
          }
        />
      ) : null}
    </div>
  );
}

export function PromptEditorForm({
  promptId = RAG_QUESTION_PREP_ID,
}: {
  promptId?: string;
}) {
  const { t } = useI18n();

  const prompt = useQuery({
    queryKey: ["prompts", promptId],
    queryFn: () => getPrompt(promptId),
  });

  if (prompt.isLoading) {
    return <p className="text-sm text-[var(--muted)]">{t("promptForm.loading")}</p>;
  }

  if (prompt.isError || !prompt.data) {
    return (
      <ErrorBox
        message={
          prompt.error instanceof Error
            ? prompt.error.message
            : t("promptForm.loadFailed")
        }
      />
    );
  }

  return (
    <PromptEditorLoaded
      key={promptEditorKey(prompt.data)}
      promptId={promptId}
      data={prompt.data}
    />
  );
}

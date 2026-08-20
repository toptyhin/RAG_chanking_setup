import { en, type Messages } from "./locales/en";
import { ru } from "./locales/ru";

export type Locale = "en" | "ru";
export type { Messages };

export const LOCALES: Locale[] = ["en", "ru"];

export const LOCALE_LABELS: Record<Locale, string> = {
  en: "EN",
  ru: "RU",
};

export const catalogs: Record<Locale, Messages> = {
  en,
  ru,
};

type Join<K, P> = K extends string | number
  ? P extends string | number
    ? `${K}${"" extends P ? "" : "."}${P}`
    : never
  : never;

type Paths<T> = T extends string
  ? ""
  : {
      [K in keyof T & string]: T[K] extends string
        ? K
        : Join<K, Paths<T[K]>>;
    }[keyof T & string];

export type TranslationKey = Paths<Messages>;

function getByPath(obj: unknown, path: string): string | undefined {
  const parts = path.split(".");
  let cur: unknown = obj;
  for (const part of parts) {
    if (cur == null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string, unknown>)[part];
  }
  return typeof cur === "string" ? cur : undefined;
}

export function interpolate(
  template: string,
  vars?: Record<string, string | number>,
): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, key: string) =>
    vars[key] != null ? String(vars[key]) : `{${key}}`,
  );
}

export function translate(
  locale: Locale,
  key: TranslationKey,
  vars?: Record<string, string | number>,
): string {
  const raw =
    getByPath(catalogs[locale], key) ?? getByPath(catalogs.en, key) ?? key;
  return interpolate(raw, vars);
}

export function htmlLang(locale: Locale): string {
  return locale === "ru" ? "ru" : "en";
}

export function bcp47(locale: Locale): string {
  return locale === "ru" ? "ru-RU" : "en-US";
}

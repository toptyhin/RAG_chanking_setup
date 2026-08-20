"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  LOCALES,
  bcp47,
  htmlLang,
  translate,
  type Locale,
  type TranslationKey,
} from "@/i18n";
import { LOCALE_STORAGE_KEY as STORAGE_KEY } from "@/lib/locale-boot";

type TranslateFn = (
  key: TranslationKey,
  vars?: Record<string, string | number>,
) => string;

type LocaleContextValue = {
  locale: Locale;
  setLocale: (value: Locale) => void;
  cycle: () => void;
  t: TranslateFn;
  bcp47: string;
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

function readStored(): Locale {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === "en" || raw === "ru") return raw;
  } catch {
    /* ignore */
  }
  return "en";
}

function applyDom(locale: Locale) {
  document.documentElement.lang = htmlLang(locale);
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    const next = readStored();
    setLocaleState(next);
    applyDom(next);
  }, []);

  const setLocale = useCallback((value: Locale) => {
    setLocaleState(value);
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch {
      /* ignore */
    }
    applyDom(value);
  }, []);

  const cycle = useCallback(() => {
    const idx = LOCALES.indexOf(locale);
    setLocale(LOCALES[(idx + 1) % LOCALES.length]!);
  }, [locale, setLocale]);

  const t = useCallback<TranslateFn>(
    (key, vars) => translate(locale, key, vars),
    [locale],
  );

  const value = useMemo(
    () => ({
      locale,
      setLocale,
      cycle,
      t,
      bcp47: bcp47(locale),
    }),
    [locale, setLocale, cycle, t],
  );

  return (
    <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
  );
}

export function useI18n(): LocaleContextValue {
  const ctx = useContext(LocaleContext);
  if (!ctx) {
    throw new Error("useI18n must be used within LocaleProvider");
  }
  return ctx;
}

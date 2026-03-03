import { createContext, useContext, useMemo, type PropsWithChildren } from "react";

import { dictionaries, type TranslationKey } from "./dictionary";
import type { Locale, TranslationParams } from "./model";

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: TranslationKey, params?: TranslationParams) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

function interpolate(value: string, params?: TranslationParams): string {
  if (!params) {
    return value;
  }

  return value.replace(/\{(\w+)\}/g, (_, token: string) => {
    const next = params[token];
    return next === undefined ? `{${token}}` : String(next);
  });
}

interface ProviderProps extends PropsWithChildren {
  locale: Locale;
  setLocale: (locale: Locale) => void;
}

export function I18nProvider({ locale, setLocale, children }: ProviderProps) {
  const value = useMemo<I18nContextValue>(() => {
    const t = (key: TranslationKey, params?: TranslationParams): string => {
      const template = dictionaries[locale][key] ?? dictionaries.en[key] ?? key;
      return interpolate(template, params);
    };

    return {
      locale,
      setLocale,
      t,
    };
  }, [locale, setLocale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used inside I18nProvider");
  }

  return context;
}

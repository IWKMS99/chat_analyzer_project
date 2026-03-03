import { useCallback, useEffect, useMemo, useState } from "react";

import type { Locale } from "../../i18n/model";

interface UrlState {
  analysisId: string | null;
  lang: Locale;
}

const LOCALE_STORAGE_KEY = "chat-analyzer-locale";

function isLocale(value: string | null): value is Locale {
  return value === "en" || value === "ru";
}

function detectBrowserLocale(): Locale {
  if (typeof navigator === "undefined") {
    return "en";
  }

  return navigator.language.toLowerCase().startsWith("ru") ? "ru" : "en";
}

function readLocaleFromStorage(): Locale | null {
  if (typeof window === "undefined") {
    return null;
  }

  const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
  return isLocale(stored) ? stored : null;
}

function readStateFromUrl(): UrlState {
  if (typeof window === "undefined") {
    return {
      analysisId: null,
      lang: "en",
    };
  }

  const params = new URLSearchParams(window.location.search);
  const analysisId = params.get("analysisId")?.trim() || null;
  const lang = isLocale(params.get("lang"))
    ? (params.get("lang") as Locale)
    : readLocaleFromStorage() || detectBrowserLocale();

  return {
    analysisId,
    lang,
  };
}

function writeStateToUrl(next: UrlState) {
  if (typeof window === "undefined") {
    return;
  }

  const params = new URLSearchParams(window.location.search);
  params.delete("view");
  params.set("lang", next.lang);
  if (next.analysisId) {
    params.set("analysisId", next.analysisId);
  } else {
    params.delete("analysisId");
  }

  const query = params.toString();
  const nextUrl = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`;
  window.history.replaceState(null, "", nextUrl);
}

export function useUrlState() {
  const [state, setState] = useState<UrlState>(() => readStateFromUrl());

  useEffect(() => {
    const handlePopState = () => {
      setState(readStateFromUrl());
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    writeStateToUrl(state);
    // Canonicalize URL once on mount with validated defaults.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, state.lang);
  }, [state.lang]);

  const setPartialState = useCallback((patch: Partial<UrlState>) => {
    setState((current) => {
      const next: UrlState = {
        ...current,
        ...patch,
      };
      writeStateToUrl(next);
      return next;
    });
  }, []);

  const api = useMemo(
    () => ({
      analysisId: state.analysisId,
      lang: state.lang,
      setAnalysisId: (analysisId: string | null) => setPartialState({ analysisId: analysisId?.trim() || null }),
      setLang: (lang: Locale) => setPartialState({ lang }),
    }),
    [setPartialState, state.analysisId, state.lang]
  );

  return api;
}

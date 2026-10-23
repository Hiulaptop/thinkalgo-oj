"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";
import { createTranslator, type Catalog, type Translator } from "@/lib/i18n/translate";

const I18nContext = createContext<Translator | null>(null);

/** Nhận catalog đã cắt của đúng ngôn ngữ request từ server; không nhận toàn bộ file dịch. */
export function I18nProvider({ catalog, children }: { catalog: Catalog; children: ReactNode }) {
  const translator = useMemo(() => createTranslator(catalog), [catalog]);
  return <I18nContext.Provider value={translator}>{children}</I18nContext.Provider>;
}

export function useI18n(): Translator {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n phải được dùng bên trong <I18nProvider>");
  return ctx;
}

import en from "@/locales/en.json";
import vi from "@/locales/vi.json";
import { DEFAULT_LOCALE } from "./config";
import type { Catalog } from "./translate";

// Thêm ngôn ngữ mới: thêm vào locales.json và import tương ứng ở đây.
const CATALOGS: Record<string, Catalog> = { en, vi };

export function getCatalog(locale: string): Catalog {
  return CATALOGS[locale] ?? CATALOGS[DEFAULT_LOCALE];
}

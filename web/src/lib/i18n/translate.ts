import { interpolate, type Params } from "./format";
import { parsePluralForms } from "./plural";

export type Catalog = {
  locale: string;
  plural: string;
  messages: Record<string, string | string[]>;
};

const CTX = "\u0004";
const ENGLISH_PLURAL = "nplurals=2; plural=n != 1;";

export type Translator = {
  locale: string;
  t: (msgid: string, params?: Params) => string;
  nt: (singular: string, plural: string, n: number, params?: Params) => string;
  pt: (context: string, msgid: string, params?: Params) => string;
};

/** Hàm dịch tương thích gettext. Thiếu bản dịch thì trả msgid tiếng Anh. */
export function createTranslator(catalog: Catalog): Translator {
  const rule = parsePluralForms(catalog.plural);
  const english = parsePluralForms(ENGLISH_PLURAL);
  const lookup = (key: string) => catalog.messages[key];

  const t: Translator["t"] = (msgid, params) => {
    const hit = lookup(msgid);
    const text = typeof hit === "string" ? hit : Array.isArray(hit) ? hit[0] : msgid;
    return interpolate(text, params);
  };

  const nt: Translator["nt"] = (singular, plural, n, params) => {
    // Như `ngettext(...) % n` của Django: không có params thì %d nhận chính n.
    const args: Params = params ?? [n];
    const hit = lookup(singular);
    if (Array.isArray(hit)) {
      return interpolate(hit[Math.min(rule.index(n), hit.length - 1)], args);
    }
    return interpolate(english.index(n) === 0 ? singular : plural, args);
  };

  const pt: Translator["pt"] = (context, msgid, params) => {
    const hit = lookup(`${context}${CTX}${msgid}`);
    const text = typeof hit === "string" ? hit : Array.isArray(hit) ? hit[0] : msgid;
    return interpolate(text, params);
  };

  return { locale: catalog.locale, t, nt, pt };
}

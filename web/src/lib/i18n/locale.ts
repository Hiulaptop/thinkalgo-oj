import { DEFAULT_LOCALE, SUPPORTED_LOCALES } from "./config";

// Cổng từ django.utils.translation.trans_real (Django 4.2) để thứ tự chọn ngôn ngữ giống hệt.
const ACCEPT_LANGUAGE_RE = /([A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})*|\*)(?:\s*;\s*q=(0(?:\.[0-9]{0,3})?|1(?:\.0{0,3})?))?(?:\s*,\s*|$)/y;
const LANGUAGE_CODE_RE = /^[a-z]{1,8}(?:-[a-z0-9]{1,8})*(?:@[a-z0-9]{1,20})?$/i;
const LANGUAGE_CODE_MAX_LENGTH = 500;

function parseAcceptLanguageUnbounded(header: string): Array<[string, number]> {
  const value = header.toLowerCase();
  const out: Array<[string, number]> = [];
  let pos = 0;
  while (pos < value.length) {
    ACCEPT_LANGUAGE_RE.lastIndex = pos;
    const m = ACCEPT_LANGUAGE_RE.exec(value);
    if (!m) return [];
    out.push([m[1], m[2] ? parseFloat(m[2]) : 1]);
    pos = ACCEPT_LANGUAGE_RE.lastIndex;
  }
  // sort ổn định, q giảm dần (như Python list.sort(reverse=True) giữ thứ tự bằng nhau)
  return out
    .map((entry, i) => ({ entry, i }))
    .sort((a, b) => b.entry[1] - a.entry[1] || a.i - b.i)
    .map(({ entry }) => entry);
}

export function parseAcceptLanguage(header: string): Array<[string, number]> {
  if (header.length <= LANGUAGE_CODE_MAX_LENGTH) return parseAcceptLanguageUnbounded(header);
  const index = header.lastIndexOf(",", LANGUAGE_CODE_MAX_LENGTH - 1);
  if (index > 0) return parseAcceptLanguageUnbounded(header.slice(0, index));
  return [];
}

/** Như get_supported_language_variant(lang_code, strict=False); null thay cho LookupError. */
export function supportedVariant(code: string | undefined | null): string | null {
  if (!code) return null;
  let langCode = code;
  if (langCode.length > LANGUAGE_CODE_MAX_LENGTH) {
    const idx = langCode.lastIndexOf("-", LANGUAGE_CODE_MAX_LENGTH - 1);
    if (idx > 0) langCode = langCode.slice(0, idx);
    else return null;
  }
  const possible = [langCode];
  let i = langCode.length;
  while ((i = langCode.lastIndexOf("-", i - 1)) > -1) {
    possible.push(langCode.slice(0, i));
    if (i === 0) break;
  }
  const generic = possible[possible.length - 1];
  for (const c of possible) {
    if (SUPPORTED_LOCALES.includes(c.toLowerCase())) return c.toLowerCase();
  }
  for (const s of SUPPORTED_LOCALES) {
    if (s.startsWith(generic + "-")) return s;
  }
  return null;
}

/** Cookie `django_language` -> Accept-Language -> mặc định, giống LocaleMiddleware. */
export function resolveLocale(cookieValue: string | undefined, acceptLanguage: string | null | undefined): string {
  if (cookieValue !== undefined) {
    if (SUPPORTED_LOCALES.includes(cookieValue)) return cookieValue;
    const fromCookie = supportedVariant(cookieValue);
    if (fromCookie) return fromCookie;
  }
  for (const [lang] of parseAcceptLanguage(acceptLanguage ?? "")) {
    if (lang === "*") break;
    if (!LANGUAGE_CODE_RE.test(lang)) continue;
    const found = supportedVariant(lang);
    if (found) return found;
  }
  return supportedVariant(DEFAULT_LOCALE) ?? DEFAULT_LOCALE;
}

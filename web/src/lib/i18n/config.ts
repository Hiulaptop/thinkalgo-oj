import cfg from "./locales.json";

export type Locale = (typeof cfg.supported)[number];

export const SUPPORTED_LOCALES: readonly string[] = cfg.supported;
/** Ngôn ngữ nguồn của msgid (không cần bản dịch). */
export const SOURCE_LOCALE = cfg.source;
/** Tên cookie mặc định của LANGUAGE_COOKIE_NAME ở Django; repo không đổi. */
export const LOCALE_COOKIE = "django_language";

function isSupported(value: string | undefined): value is string {
  return !!value && SUPPORTED_LOCALES.includes(value);
}

/** Bằng LANGUAGE_CODE của Django ở production (`vi`); ghi đè bằng biến môi trường DEFAULT_LOCALE. */
export const DEFAULT_LOCALE: string = isSupported(process.env.DEFAULT_LOCALE)
  ? process.env.DEFAULT_LOCALE
  : cfg.default;

"use server";

import { cookies } from "next/headers";
import { LOCALE_COOKIE, SUPPORTED_LOCALES } from "./config";

const ONE_YEAR = 60 * 60 * 24 * 365;

/** Ghi cùng cookie `django_language` để trang Jinja và Next.js luôn đồng ý về ngôn ngữ. */
export async function setLocaleAction(locale: string): Promise<void> {
  if (!SUPPORTED_LOCALES.includes(locale)) return;
  const store = await cookies();
  store.set(LOCALE_COOKIE, locale, { path: "/", sameSite: "lax", maxAge: ONE_YEAR });
}

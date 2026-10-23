import { cookies, headers } from "next/headers";
import { getCatalog } from "./catalogs";
import { LOCALE_COOKIE } from "./config";
import { resolveLocale } from "./locale";
import { createTranslator, type Translator } from "./translate";

/** Ngôn ngữ của request hiện tại (dùng Dynamic API nên route sẽ render động). */
export async function getLocale(): Promise<string> {
  const cookieStore = await cookies();
  const headerStore = await headers();
  return resolveLocale(cookieStore.get(LOCALE_COOKIE)?.value, headerStore.get("accept-language"));
}

export async function getTranslator(): Promise<Translator> {
  return createTranslator(getCatalog(await getLocale()));
}

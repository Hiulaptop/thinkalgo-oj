import type { Metadata } from "next";
import type { ReactNode } from "react";
import "@fontsource-variable/nunito";
import "@fontsource-variable/baloo-2";
import "@fontsource-variable/jetbrains-mono";
import "./globals.css";
import { themeInitScript } from "@/lib/theme-script";
import { UiStoreProvider } from "@/components/providers/ui-store-provider";
import { Navbar } from "@/components/shell/navbar";
import { Footer } from "@/components/shell/footer";
import { I18nProvider } from "@/components/providers/i18n-provider";
import { getCatalog } from "@/lib/i18n/catalogs";
import { getLocale, getTranslator } from "@/lib/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getTranslator();
  return {
    title: { default: "ThinkAlgo OJ", template: "%s | ThinkAlgo OJ" },
    description: t("Competitive programming online judge ThinkAlgo OJ."),
  };
}

export default async function RootLayout({ children }: { children: ReactNode }) {
  const locale = await getLocale();
  const { t } = await getTranslator();
  return (
    <html lang={locale} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="font-body">
        <I18nProvider catalog={getCatalog(locale)}>
        <UiStoreProvider>
          <a
            href="#main"
            className="focus-ring absolute left-4 top-2 z-50 -translate-y-20 rounded-button border-2 border-edge bg-amber px-4 py-2 font-extrabold text-cocoa focus:translate-y-0"
          >
            {t("Skip navigation")}
          </a>
          <Navbar />
          <main id="main" className="mx-auto w-full max-w-[1280px] px-4 pt-8">
            {children}
          </main>
          <Footer />
        </UiStoreProvider>
        </I18nProvider>
      </body>
    </html>
  );
}

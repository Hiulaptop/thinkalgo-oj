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

export const metadata: Metadata = {
  title: { default: "ThinkAlgo OJ", template: "%s | ThinkAlgo OJ" },
  description: "Hệ thống chấm bài lập trình thi đấu ThinkAlgo OJ.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="font-body">
        <UiStoreProvider>
          <a
            href="#main"
            className="focus-ring absolute left-4 top-2 z-50 -translate-y-20 rounded-button border-2 border-edge bg-amber px-4 py-2 font-extrabold text-cocoa focus:translate-y-0"
          >
            Bỏ qua điều hướng
          </a>
          <Navbar />
          <main id="main" className="mx-auto w-full max-w-[1280px] px-4 pt-8">
            {children}
          </main>
          <Footer />
        </UiStoreProvider>
      </body>
    </html>
  );
}

"use client";

import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUiStore } from "@/components/providers/ui-store-provider";
import { useI18n } from "@/components/providers/i18n-provider";

export function ThemeToggle() {
  const { t } = useI18n();
  const hydrated = useUiStore((s) => s.hydrated);
  const resolved = useUiStore((s) => s.resolvedTheme);
  const setTheme = useUiStore((s) => s.setTheme);

  // Trước khi hydrate, nhãn trung tính để HTML server và client khớp nhau.
  const label = !hydrated
    ? t("Toggle light/dark mode")
    : resolved === "dark"
      ? t("Switch to light mode")
      : t("Switch to dark mode");

  return (
    <Button
      type="button"
      variant="secondary"
      size="icon"
      aria-label={label}
      title={label}
      onClick={() => setTheme(resolved === "dark" ? "light" : "dark")}
    >
      <Moon aria-hidden="true" className="block [[data-theme=dark]_&]:hidden" />
      <Sun aria-hidden="true" className="hidden [[data-theme=dark]_&]:block" />
    </Button>
  );
}

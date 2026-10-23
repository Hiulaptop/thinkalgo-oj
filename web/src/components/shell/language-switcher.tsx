"use client";

import { useTransition } from "react";
import { Languages } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/components/providers/i18n-provider";
import { setLocaleAction } from "@/lib/i18n/actions";

// Tên ngôn ngữ luôn viết bằng chính ngôn ngữ đó nên không đi qua t().
const LABELS: Record<string, string> = { en: "English", vi: "Tiếng Việt" };

export function LanguageSwitcher() {
  const { t, locale } = useI18n();
  const [pending, startTransition] = useTransition();
  const next = locale === "vi" ? "en" : "vi";
  const label = `${t("Language")}: ${LABELS[next]}`;

  return (
    <Button
      type="button"
      variant="secondary"
      size="sm"
      aria-label={label}
      title={label}
      disabled={pending}
      lang={next}
      onClick={() => startTransition(() => setLocaleAction(next))}
    >
      <Languages aria-hidden="true" />
      <span aria-hidden="true">{LABELS[next]}</span>
    </Button>
  );
}

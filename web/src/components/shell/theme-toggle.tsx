"use client";

import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUiStore } from "@/components/providers/ui-store-provider";

export function ThemeToggle() {
  const hydrated = useUiStore((s) => s.hydrated);
  const resolved = useUiStore((s) => s.resolvedTheme);
  const setTheme = useUiStore((s) => s.setTheme);

  // Trước khi hydrate, nhãn trung tính để HTML server và client khớp nhau.
  const label = !hydrated
    ? "Đổi chế độ sáng/tối"
    : resolved === "dark"
      ? "Chuyển sang chế độ sáng"
      : "Chuyển sang chế độ tối";

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

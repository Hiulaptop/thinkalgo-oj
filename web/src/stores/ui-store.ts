import { createStore } from "zustand/vanilla";

export type ThemePreference = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "thinkalgo-theme";

export interface UiState {
  /** Lựa chọn của người dùng; "system" nghĩa là theo hệ điều hành. */
  theme: ThemePreference;
  resolvedTheme: ResolvedTheme;
  /** false cho tới khi client đọc xong lựa chọn đã lưu (tránh lệch hydration). */
  hydrated: boolean;
  mobileMenuOpen: boolean;
  hydrate: () => void;
  setTheme: (theme: ThemePreference) => void;
  syncSystemTheme: () => void;
  setMobileMenuOpen: (open: boolean) => void;
}

function systemTheme(): ResolvedTheme {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function resolve(theme: ThemePreference): ResolvedTheme {
  return theme === "system" ? systemTheme() : theme;
}

function readStoredTheme(): ThemePreference {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    // localStorage có thể bị chặn (chế độ riêng tư); dùng theo hệ điều hành.
  }
  return "system";
}

function writeStoredTheme(theme: ThemePreference) {
  try {
    if (theme === "system") window.localStorage.removeItem(THEME_STORAGE_KEY);
    else window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Bỏ qua: lựa chọn vẫn áp dụng cho phiên hiện tại.
  }
}

function applyResolvedTheme(resolved: ResolvedTheme) {
  document.documentElement.dataset.theme = resolved;
}

/**
 * Store tạo riêng cho từng provider (không singleton ở module) để state
 * giao diện không bị rò giữa các request khi render phía server.
 * Chỉ chứa state giao diện, không chứa dữ liệu nghiệp vụ.
 */
export function createUiStore() {
  return createStore<UiState>()((set, get) => ({
    theme: "system",
    resolvedTheme: "light",
    hydrated: false,
    mobileMenuOpen: false,
    hydrate: () => {
      const theme = readStoredTheme();
      const resolvedTheme = resolve(theme);
      applyResolvedTheme(resolvedTheme);
      set({ theme, resolvedTheme, hydrated: true });
    },
    setTheme: (theme) => {
      const resolvedTheme = resolve(theme);
      writeStoredTheme(theme);
      applyResolvedTheme(resolvedTheme);
      set({ theme, resolvedTheme });
    },
    syncSystemTheme: () => {
      if (get().theme !== "system") return;
      const resolvedTheme = systemTheme();
      applyResolvedTheme(resolvedTheme);
      set({ resolvedTheme });
    },
    setMobileMenuOpen: (mobileMenuOpen) => set({ mobileMenuOpen }),
  }));
}

export type UiStore = ReturnType<typeof createUiStore>;

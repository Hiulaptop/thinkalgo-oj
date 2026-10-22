import { createStore } from "zustand/vanilla";

/** Mặc định là "light"; chỉ "dark" khi người dùng chủ động chọn. */
export type ThemePreference = "light" | "dark";
export type ResolvedTheme = ThemePreference;

export const THEME_STORAGE_KEY = "thinkalgo-theme";

export interface UiState {
  /** Lựa chọn của người dùng, mặc định sáng (không theo hệ điều hành). */
  theme: ThemePreference;
  resolvedTheme: ResolvedTheme;
  /** false cho tới khi client đọc xong lựa chọn đã lưu (tránh lệch hydration). */
  hydrated: boolean;
  mobileMenuOpen: boolean;
  hydrate: () => void;
  setTheme: (theme: ThemePreference) => void;
  setMobileMenuOpen: (open: boolean) => void;
}

function readStoredTheme(): ThemePreference {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "dark") return "dark";
  } catch {
    // localStorage có thể bị chặn (chế độ riêng tư); dùng chế độ sáng mặc định.
  }
  return "light";
}

function writeStoredTheme(theme: ThemePreference) {
  try {
    if (theme === "light") window.localStorage.removeItem(THEME_STORAGE_KEY);
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
  return createStore<UiState>()((set) => ({
    theme: "light",
    resolvedTheme: "light",
    hydrated: false,
    mobileMenuOpen: false,
    hydrate: () => {
      const theme = readStoredTheme();
      applyResolvedTheme(theme);
      set({ theme, resolvedTheme: theme, hydrated: true });
    },
    setTheme: (theme) => {
      writeStoredTheme(theme);
      applyResolvedTheme(theme);
      set({ theme, resolvedTheme: theme });
    },
    setMobileMenuOpen: (mobileMenuOpen) => set({ mobileMenuOpen }),
  }));
}

export type UiStore = ReturnType<typeof createUiStore>;

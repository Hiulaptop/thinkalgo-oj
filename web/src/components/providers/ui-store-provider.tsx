"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useStore } from "zustand";
import { createUiStore, type UiState, type UiStore } from "@/stores/ui-store";

const UiStoreContext = createContext<UiStore | null>(null);

export function UiStoreProvider({ children }: { children: ReactNode }) {
  const [store] = useState(createUiStore);

  useEffect(() => {
    store.getState().hydrate();
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => store.getState().syncSystemTheme();
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [store]);

  return <UiStoreContext.Provider value={store}>{children}</UiStoreContext.Provider>;
}

export function useUiStore<T>(selector: (state: UiState) => T): T {
  const store = useContext(UiStoreContext);
  if (!store) throw new Error("useUiStore phải được dùng bên trong <UiStoreProvider>");
  return useStore(store, selector);
}

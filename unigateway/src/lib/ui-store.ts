"use client";

import { create } from "zustand";

interface UiState {
  sidebarCollapsed: boolean;
  commandOpen: boolean;
  mobileNav: boolean;
  toggleSidebar: () => void;
  setCommandOpen: (open: boolean) => void;
  setMobileNav: (open: boolean) => void;
}

export const useUi = create<UiState>((set) => ({
  sidebarCollapsed: false,
  commandOpen: false,
  mobileNav: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setCommandOpen: (open) => set({ commandOpen: open }),
  setMobileNav: (open) => set({ mobileNav: open }),
}));

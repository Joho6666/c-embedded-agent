"use client";

import { create } from "zustand";

interface UiState {
  sidebarCollapsed: boolean;
  commandOpen: boolean;
  addProviderOpen: boolean;
  addCredentialOpen: boolean;
  addCredentialProviderId?: string;
  credentialDrawerId?: string;
  requestDrawerId?: string;
  createKeyOpen: boolean;
  createVirtualOpen: boolean;
  toggleSidebar: () => void;
  setCommandOpen: (open: boolean) => void;
  openAddProvider: () => void;
  closeAddProvider: () => void;
  openAddCredential: (providerId?: string) => void;
  closeAddCredential: () => void;
  openCredential: (id?: string) => void;
  openRequest: (id?: string) => void;
  setCreateKeyOpen: (open: boolean) => void;
  setCreateVirtualOpen: (open: boolean) => void;
}

export const useUi = create<UiState>((set) => ({
  sidebarCollapsed: false,
  commandOpen: false,
  addProviderOpen: false,
  addCredentialOpen: false,
  createKeyOpen: false,
  createVirtualOpen: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setCommandOpen: (commandOpen) => set({ commandOpen }),
  openAddProvider: () => set({ addProviderOpen: true }),
  closeAddProvider: () => set({ addProviderOpen: false }),
  openAddCredential: (providerId) => set({ addCredentialOpen: true, addCredentialProviderId: providerId }),
  closeAddCredential: () => set({ addCredentialOpen: false, addCredentialProviderId: undefined }),
  openCredential: (id) => set({ credentialDrawerId: id }),
  openRequest: (id) => set({ requestDrawerId: id }),
  setCreateKeyOpen: (createKeyOpen) => set({ createKeyOpen }),
  setCreateVirtualOpen: (createVirtualOpen) => set({ createVirtualOpen }),
}));

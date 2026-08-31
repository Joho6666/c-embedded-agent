"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { tools as seed } from "@/lib/mock/tools";
import type { ToolConnection, ToolItem } from "@/types/tools";

interface ToolsState {
  items: ToolItem[];
  setStatus: (id: string, status: ToolConnection, extra?: Partial<ToolItem>) => void;
  connect: (id: string) => void;
  disconnect: (id: string) => void;
}

export const useTools = create<ToolsState>()(
  persist(
    (set) => ({
      items: seed,
      setStatus: (id, status, extra) =>
        set((s) => ({
          items: s.items.map((t) => (t.id === id ? { ...t, status, lastChecked: new Date().toISOString().slice(0, 16).replace("T", " "), ...extra } : t)),
        })),
      connect: (id) =>
        set((s) => ({
          items: s.items.map((t) =>
            t.id === id
              ? {
                  ...t,
                  status: "connected",
                  lastChecked: new Date().toISOString().slice(0, 16).replace("T", " "),
                  detail: t.id === "keilmdk" ? "V5.39 · UV4.exe" : t.detail,
                }
              : t,
          ),
        })),
      disconnect: (id) =>
        set((s) => ({
          items: s.items.map((t) => (t.id === id ? { ...t, status: "disconnected" } : t)),
        })),
    }),
    { name: "cea-tools-v2", partialize: (s) => ({ items: s.items }) },
  ),
);

"use client";

import { create } from "zustand";
import { API_BASE } from "@/lib/api/client";

export type BackendMode = "live" | "demo" | "offline";

interface LiveState {
  mode: BackendMode;
  lastError?: string;
  gcc?: string;
  refresh: () => Promise<void>;
}

export const useLive = create<LiveState>((set) => ({
  mode: "demo",
  refresh: async () => {
    const base = API_BASE || "http://127.0.0.1:8000";
    try {
      const res = await fetch(`${base}/api/health`, { cache: "no-store" });
      if (!res.ok) throw new Error(String(res.status));
      const data = (await res.json()) as { ok?: boolean; gcc?: string };
      set({ mode: "live", lastError: undefined, gcc: data.gcc });
    } catch (e) {
      set({ mode: API_BASE ? "offline" : "demo", lastError: e instanceof Error ? e.message : "offline" });
    }
  },
}));

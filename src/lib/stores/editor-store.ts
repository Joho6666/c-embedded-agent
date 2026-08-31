"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { CodeFile } from "@/types/debug";
import type { CodePatch } from "@/types/patch";
import { initialFiles } from "@/lib/mock/files";

interface EditorFile extends CodeFile {
  saved: string;
}

interface EditorState {
  files: Record<string, EditorFile>;
  activeFile: string;
  revealLine?: number;
  tabs: string[];
  patches: CodePatch[];
  lastAccepted?: CodePatch;
  openFile: (path: string, line?: number) => void;
  closeTab: (path: string) => void;
  setContent: (path: string, content: string) => void;
  saveFile: (path?: string) => void;
  addPatch: (patch: CodePatch) => void;
  acceptPatch: (id: string) => void;
  rejectPatch: (id: string) => void;
  acceptAll: () => void;
  undoLastAiChange: () => void;
  resetFiles: () => void;
  loadWorkspace: (files: Record<string, { path: string; language: string; content: string }>) => void;
}

function wrap(files: Record<string, CodeFile>): Record<string, EditorFile> {
  const out: Record<string, EditorFile> = {};
  for (const [k, v] of Object.entries(files)) {
    out[k] = { ...v, saved: v.content };
  }
  return out;
}

export const useEditor = create<EditorState>()(
  persist(
    (set, get) => ({
  files: wrap(initialFiles),
  activeFile: "/Core/Src/main.c",
  tabs: ["/Core/Src/main.c"],
  patches: [],

  openFile: (path, line) =>
    set((s) => ({
      activeFile: path,
      revealLine: line,
      tabs: s.tabs.includes(path) ? s.tabs : [...s.tabs, path],
    })),
  closeTab: (path) =>
    set((s) => {
      const tabs = s.tabs.filter((t) => t !== path);
      return { tabs, activeFile: s.activeFile === path ? (tabs[0] ?? s.activeFile) : s.activeFile };
    }),
  setContent: (path, content) =>
    set((s) => ({
      files: { ...s.files, [path]: { ...(s.files[path] ?? { path, language: "c", saved: content }), content } },
    })),
  saveFile: (path) => {
    const s = get();
    const p = path ?? s.activeFile;
    const f = s.files[p];
    if (!f) return;
    set({ files: { ...s.files, [p]: { ...f, saved: f.content } } });
    void (async () => {
      try {
        const { useLive } = await import("./live-store");
        const { useProject } = await import("./project-store");
        const { API_BASE } = await import("@/lib/api/client");
        if (useLive.getState().mode !== "live") return;
        const pid = useProject.getState().projectId;
        const rel = p.replace(/^\//, "");
        await fetch(`${API_BASE}/api/projects/${pid}/file`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: rel, content: f.content }),
        });
      } catch {
        /* demo / offline */
      }
    })();
  },
  addPatch: (patch) =>
    set((s) => ({
      patches: [...s.patches.filter((p) => !(p.path === patch.path && p.status === "pending")), patch],
      activeFile: patch.path,
      tabs: s.tabs.includes(patch.path) ? s.tabs : [...s.tabs, patch.path],
    })),
  acceptPatch: (id) =>
    set((s) => {
      const patch = s.patches.find((p) => p.id === id);
      if (!patch || patch.status !== "pending") return s;
      const f = s.files[patch.path];
      return {
        lastAccepted: patch,
        files: {
          ...s.files,
          [patch.path]: {
            path: patch.path,
            language: f?.language ?? "c",
            content: patch.proposed,
            saved: patch.proposed,
          },
        },
        patches: s.patches.map((p) => (p.id === id ? { ...p, status: "accepted" as const } : p)),
      };
    }),
  rejectPatch: (id) =>
    set((s) => ({
      patches: s.patches.map((p) => (p.id === id ? { ...p, status: "rejected" as const } : p)),
    })),
  acceptAll: () => {
    const pending = get().patches.filter((p) => p.status === "pending");
    for (const p of pending) get().acceptPatch(p.id);
  },
  undoLastAiChange: () =>
    set((s) => {
      const last = s.lastAccepted;
      if (!last) return s;
      const f = s.files[last.path];
      return {
        files: f
          ? { ...s.files, [last.path]: { ...f, content: last.original, saved: last.original } }
          : s.files,
        patches: s.patches.map((p) => (p.id === last.id ? { ...p, status: "rejected" as const } : p)),
        lastAccepted: undefined,
      };
    }),
  resetFiles: () =>
    set({
      files: wrap(initialFiles),
      activeFile: "/Core/Src/main.c",
      tabs: ["/Core/Src/main.c"],
      patches: [],
      lastAccepted: undefined,
    }),
  loadWorkspace: (incoming) =>
    set({
      files: wrap(incoming),
      activeFile: incoming["/Core/Src/main.c"] ? "/Core/Src/main.c" : Object.keys(incoming)[0] ?? "/Core/Src/main.c",
      tabs: incoming["/Core/Src/main.c"] ? ["/Core/Src/main.c"] : Object.keys(incoming).slice(0, 1),
      patches: [],
      lastAccepted: undefined,
    }),
    }),
    { name: "cea-editor", partialize: (s) => ({ tabs: s.tabs, activeFile: s.activeFile }) },
  ),
);

"use client";

import { create } from "zustand";
import type { SerialLine } from "@/types/debug";

interface TerminalState {
  terminalLines: string[];
  buildLines: string[];
  serialLines: SerialLine[];
  appendTerminal: (lines: string[]) => void;
  appendBuild: (lines: string[]) => void;
  appendSerial: (lines: SerialLine[]) => void;
  reset: () => void;
}

export const useTerminal = create<TerminalState>((set) => ({
  terminalLines: ["$ ready", "C-Embedded Agent 工作台已就绪。"],
  buildLines: [],
  serialLines: [],
  appendTerminal: (lines) => set((s) => ({ terminalLines: [...s.terminalLines, ...lines] })),
  appendBuild: (lines) => set((s) => ({ buildLines: [...s.buildLines, ...lines] })),
  appendSerial: (lines) => set((s) => ({ serialLines: [...s.serialLines, ...lines] })),
  reset: () =>
    set({
      terminalLines: ["$ agent run"],
      buildLines: [],
      serialLines: [],
    }),
}));

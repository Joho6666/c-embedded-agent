"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { HardwareContext, PinConflict } from "@/types/hardware";
import { defaultHardware } from "@/lib/mock/hardware";

interface HardwareState {
  context: HardwareContext;
  conflict?: PinConflict;
  setContext: (c: Partial<HardwareContext>) => void;
  setConflict: (c?: PinConflict) => void;
}

export const useHardware = create<HardwareState>()(
  persist(
    (set) => ({
      context: defaultHardware,
      conflict: undefined,
      setContext: (c) => set((s) => ({ context: { ...s.context, ...c } })),
      setConflict: (c) => set({ conflict: c }),
    }),
    { name: "cea-hw", partialize: (s) => ({ context: s.context }) },
  ),
);

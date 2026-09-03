"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { HardwareContext, PinConflict } from "@/types/hardware";
import type { IocAnalysis } from "@/types/ioc";
import type { HardwarePipelineResult } from "@/types/hardware-run";
import { defaultHardware } from "@/lib/mock/hardware";

interface HardwareState {
  context: HardwareContext;
  conflict?: PinConflict;
  ioc?: IocAnalysis;
  hardwareRun?: HardwarePipelineResult;
  setContext: (c: Partial<HardwareContext>) => void;
  setConflict: (c?: PinConflict) => void;
  setIoc: (a?: IocAnalysis) => void;
  setHardwareRun: (r?: HardwarePipelineResult) => void;
}

export const useHardware = create<HardwareState>()(
  persist(
    (set) => ({
      context: defaultHardware,
      conflict: undefined,
      ioc: undefined,
      hardwareRun: undefined,
      setContext: (c) => set((s) => ({ context: { ...s.context, ...c } })),
      setConflict: (c) => set({ conflict: c }),
      setIoc: (a) => set({ ioc: a }),
      setHardwareRun: (r) => set({ hardwareRun: r }),
    }),
    { name: "cea-hw-v2", partialize: (s) => ({ context: s.context, ioc: s.ioc }) },
  ),
);

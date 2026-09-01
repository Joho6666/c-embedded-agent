"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { runHardwarePipeline } from "@/lib/api/validation";
import { useHardware } from "@/lib/stores/hardware-store";
import { useProject } from "@/lib/stores/project-store";
import { useLive } from "@/lib/stores/live-store";

export function HardwareRunButton() {
  const projectId = useProject((s) => s.projectId);
  const ctx = useHardware((s) => s.context);
  const setRun = useHardware((s) => s.setHardwareRun);
  const mode = useLive((s) => s.mode);
  const [busy, setBusy] = useState(false);

  return (
    <Button
      size="sm"
      disabled={busy}
      onClick={() => {
        if (mode !== "live") {
          setRun({ available: false, reason: "Backend capability unavailable", steps: [] });
          return;
        }
        setBusy(true);
        void runHardwarePipeline({
          projectId,
          serialDevice: ctx.serialPort || undefined,
          baud: ctx.serialBaud,
          expect: "Hello",
        })
          .then(setRun)
          .finally(() => setBusy(false));
      }}
    >
      {busy ? "Running…" : "Run on Device"}
    </Button>
  );
}

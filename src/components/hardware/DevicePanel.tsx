"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { API_BASE } from "@/lib/api/client";
import { useHardware } from "@/lib/stores/hardware-store";
import { useLive } from "@/lib/stores/live-store";
import { useProject } from "@/lib/stores/project-store";

export function DevicePanel() {
  const ctx = useHardware((s) => s.context);
  const mode = useLive((s) => s.mode);
  const projectId = useProject((s) => s.projectId);
  const router = useRouter();
  const [stlink, setStlink] = useState<string>("Unknown");
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string>("");

  useEffect(() => {
    if (mode !== "live") return;
    void fetch(`${API_BASE}/api/tools/status`)
      .then((r) => (r.ok ? r.json() : []))
      .then((rows: Array<{ id: string; installed?: boolean; version?: string }>) => {
        const t = rows.find((x) => x.id === "stlink" || x.id === "openocd");
        if (!t) setStlink("Not detected");
        else setStlink(t.installed ? t.version || "Connected" : "Disconnected");
      })
      .catch(() => setStlink("Backend capability unavailable"));
  }, [mode]);

  const flash = async () => {
    if (mode !== "live") {
      setMsg("Backend capability unavailable");
      return;
    }
    setBusy("flash");
    try {
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/flash`, { method: "POST" });
      const data = (await res.json().catch(() => ({}))) as { success?: boolean; error?: string };
      setMsg(res.ok && data.success ? "Flash Verified" : data.error || `${res.status} flash`);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "flash failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      <div className="border-b border-border px-3 py-2 text-[11px] font-medium text-muted-foreground">Device</div>
      <dl className="space-y-1.5 p-3 text-[12px]">
        <div className="flex justify-between">
          <dt className="text-muted-foreground">ST-Link</dt>
          <dd className="font-mono">{mode === "live" ? stlink : "DEMO"}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted-foreground">MCU</dt>
          <dd className="font-mono">{ctx.mcu}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted-foreground">Serial</dt>
          <dd className="font-mono">{ctx.serialPort}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted-foreground">Baud</dt>
          <dd className="font-mono">{ctx.serialBaud}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted-foreground">State</dt>
          <dd className="font-mono">{busy ?? "Idle"}</dd>
        </div>
      </dl>
      <div className="flex flex-wrap gap-1 px-3 pb-3">
        <Button size="sm" variant="outline" onClick={() => void flash()} disabled={busy === "flash"}>
          Flash
        </Button>
        <Button size="sm" variant="outline" onClick={() => router.push("/serial")}>
          Open Serial
        </Button>
        <Button size="sm" variant="outline" onClick={() => router.push("/serial")}>
          Reconnect
        </Button>
        <Button size="sm" variant="outline" disabled title="Reset 由 OpenOCD verify reset 完成">
          Reset
        </Button>
      </div>
      {msg && <div className="px-3 pb-3 text-[11px] text-muted-foreground">{msg}</div>}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { SerialMonitor } from "@/components/terminal/SerialMonitor";
import { serialLog } from "@/lib/mock/build";
import { useTerminal } from "@/lib/stores/terminal-store";
import { useLive } from "@/lib/stores/live-store";
import { API_BASE } from "@/lib/api/client";
import { Button } from "@/components/ui/button";

interface Port {
  device: string;
  description: string;
}

export default function SerialPage() {
  const liveLines = useTerminal((s) => s.serialLines);
  const mode = useLive((s) => s.mode);
  const [ports, setPorts] = useState<Port[]>([]);
  const [device, setDevice] = useState("COM3");
  const [baud, setBaud] = useState(115200);
  const [hint, setHint] = useState("");

  useEffect(() => {
    if (mode !== "live") return;
    void fetch(`${API_BASE}/api/serial/ports`)
      .then((r) => (r.ok ? r.json() : []))
      .then((rows: Port[]) => {
        setPorts(rows);
        if (rows[0]?.device) setDevice(rows[0].device);
      })
      .catch(() => setPorts([]));
  }, [mode]);

  const connect = async () => {
    const r = await fetch(`${API_BASE}/api/serial/connect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device, baud }),
    });
    setHint(r.ok ? `已连接 ${device}` : `连接失败 ${r.status}`);
  };

  return (
    <div className="flex h-full flex-col p-5">
      <h1 className="mb-3 text-[18px] font-semibold">串口监视器</h1>
      {mode === "live" ? (
        <div className="mb-3 flex flex-wrap items-center gap-2 text-[12px]">
          <select className="rounded-sm border border-border bg-panel px-2 py-1" value={device} onChange={(e) => setDevice(e.target.value)}>
            {(ports.length ? ports : [{ device, description: "" }]).map((p) => (
              <option key={p.device} value={p.device}>
                {p.device} {p.description}
              </option>
            ))}
          </select>
          <select className="rounded-sm border border-border bg-panel px-2 py-1" value={baud} onChange={(e) => setBaud(Number(e.target.value))}>
            <option value={9600}>9600</option>
            <option value={115200}>115200</option>
          </select>
          <Button size="sm" onClick={() => void connect()}>
            连接
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => void fetch(`${API_BASE}/api/serial/disconnect`, { method: "POST" })}
          >
            断开
          </Button>
          <span className="text-muted-foreground">{hint || `${ports.length} 个端口`}</span>
        </div>
      ) : (
        <p className="mb-3 text-[12px] text-muted-foreground">DEMO · COM3 · 115200</p>
      )}
      <div className="min-h-0 flex-1 overflow-hidden rounded-md border border-border">
        <SerialMonitor lines={liveLines.length ? liveLines : serialLog} port={device} baud={baud} />
      </div>
    </div>
  );
}

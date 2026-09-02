"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { API_BASE } from "@/lib/api/client";
import { useLive } from "@/lib/stores/live-store";
import { useHardware } from "@/lib/stores/hardware-store";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";
import { StatusDot } from "@/components/common/StatusDot";

interface Port {
  device: string;
  description: string;
}

export function SerialMonitor({ compact = false }: { compact?: boolean }) {
  const mode = useLive((s) => s.mode);
  const setContext = useHardware((s) => s.setContext);
  const ctx = useHardware((s) => s.context);
  const [ports, setPorts] = useState<Port[]>([]);
  const [device, setDevice] = useState(ctx.serialPort || "");
  const [baud, setBaud] = useState(ctx.serialBaud || 115200);
  const [connected, setConnected] = useState(false);
  const [paused, setPaused] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [lines, setLines] = useState<string[]>([]);
  const [send, setSend] = useState("");
  const [hint, setHint] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (mode !== "live") return;
    void fetch(`${API_BASE}/api/serial/ports`)
      .then((r) => (r.ok ? r.json() : []))
      .then((rows: Port[]) => {
        setPorts(Array.isArray(rows) ? rows : []);
        if (!device && rows[0]?.device) setDevice(rows[0].device);
      })
      .catch(() => setPorts([]));
  }, [mode, device]);

  useEffect(() => {
    if (mode !== "live" || paused || !connected) return;
    const t = window.setInterval(() => {
      void fetch(`${API_BASE}/api/serial/lines`)
        .then((r) => (r.ok ? r.json() : []))
        .then((rows: Array<{ text: string }>) => {
          if (Array.isArray(rows)) setLines(rows.map((x) => x.text));
        })
        .catch(() => undefined);
    }, 500);
    return () => window.clearInterval(t);
  }, [mode, paused, connected]);

  useEffect(() => {
    if (autoScroll && ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [lines, autoScroll]);

  const connect = async () => {
    if (!device) {
      setHint("No serial port");
      return;
    }
    const r = await fetch(`${API_BASE}/api/serial/connect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device, baud }),
    });
    if (r.ok) {
      setConnected(true);
      setHint(`已连接 ${device}`);
      setContext({ serialPort: device, serialBaud: baud });
    } else {
      setConnected(false);
      setHint(`连接失败 ${r.status}`);
    }
  };

  if (mode !== "live") {
    return (
      <div className="p-3">
        <CapabilityBanner reason="Serial Not Connected — 需要 LIVE 后端，不会显示假 Connected。" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-terminal">
      <div className="flex flex-wrap items-center gap-2 border-b border-border px-2 py-1.5 text-[11px]">
        <StatusDot status={connected ? "connected" : "not_detected"} />
        <select
          className="h-6 rounded-sm border border-border bg-panel px-1"
          value={device}
          onChange={(e) => setDevice(e.target.value)}
        >
          {(ports.length ? ports : device ? [{ device, description: "" }] : []).map((p) => (
            <option key={p.device} value={p.device}>
              {p.device}
            </option>
          ))}
          {!ports.length && !device && <option value="">No port</option>}
        </select>
        <select
          className="h-6 rounded-sm border border-border bg-panel px-1"
          value={baud}
          onChange={(e) => setBaud(Number(e.target.value))}
        >
          <option value={9600}>9600</option>
          <option value={115200}>115200</option>
        </select>
        <Button size="sm" onClick={() => void connect()}>
          连接
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            void fetch(`${API_BASE}/api/serial/disconnect`, { method: "POST" });
            setConnected(false);
          }}
        >
          断开
        </Button>
        <Button size="sm" variant="outline" onClick={() => setPaused((v) => !v)}>
          {paused ? "继续" : "暂停"}
        </Button>
        <Button size="sm" variant="outline" onClick={() => setLines([])}>
          清除
        </Button>
        <label className="flex items-center gap-1 text-muted-foreground">
          <input type="checkbox" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} />
          自动滚动
        </label>
        <span className="text-muted-foreground">{hint || (connected ? "Connected" : "Not Connected")}</span>
      </div>
      <div ref={ref} className="terminal min-h-0 flex-1 overflow-auto px-3 py-2 text-[12px] leading-5">
        {lines.length === 0 && <div className="text-muted-foreground">等待串口数据…</div>}
        {lines.map((t, i) => (
          <div key={`${i}-${t}`}>
            <span className="text-muted-foreground">[{String(i).padStart(2, "0")}]</span> {t}
          </div>
        ))}
      </div>
      {!compact && (
        <form
          className="flex gap-1 border-t border-border p-1"
          onSubmit={(e) => {
            e.preventDefault();
            if (send) setLines((xs) => [...xs, `> ${send}`]);
            setSend("");
          }}
        >
          <input
            className="h-7 flex-1 rounded-sm border border-border bg-panel px-2 text-[12px]"
            value={send}
            onChange={(e) => setSend(e.target.value)}
            placeholder="发送…"
          />
          <Button size="sm" type="submit">
            发送
          </Button>
        </form>
      )}
    </div>
  );
}

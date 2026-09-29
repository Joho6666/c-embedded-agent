"use client";

import { useCallback, useEffect, useState } from "react";
import { StatusBadge } from "@/components/common/StatusBadge";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";
import { useLive } from "@/lib/stores/live-store";
import { API_BASE } from "@/lib/api/client";

interface HardwareDevice {
  id: string;
  platformId?: string;
  platformHint?: string | null;
  board?: string;
  mcu?: string;
  mcuEvidence?: string | null;
  debugProbe?: string | null;
  serialPort?: string | null;
  capabilities?: string[];
  status: string;
  lastSeenAt?: string | null;
  source?: string;
}

interface Probe {
  id: string;
  label: string;
  toolInstalled?: boolean;
  presence: string;
  detail?: string | null;
}

interface Report {
  generatedAt?: string;
  probes?: Probe[];
  serialPorts?: { device: string; description?: string; usbName?: string | null; kind?: string | null; vid?: string | null; pid?: string | null }[];
  devices?: HardwareDevice[];
  exactMcu?: string;
  nextSteps?: string[];
}

interface MapData {
  available: boolean;
  devices?: { id: string; board?: string; platform?: string; serial?: string; capabilities?: string[]; tags?: string[] }[];
}

export default function HardwareLabPage() {
  const mode = useLive((s) => s.mode);
  const [devices, setDevices] = useState<HardwareDevice[] | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [map, setMap] = useState<MapData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [d, r, m] = await Promise.all([
        fetch(`${API_BASE}/api/hardware/devices`).then((x) => x.json()),
        fetch(`${API_BASE}/api/hardware/discovery-report`).then((x) => x.json()),
        fetch(`${API_BASE}/api/hardware/map`).then((x) => x.json()),
      ]);
      setDevices(Array.isArray(d) ? d : []);
      setReport(r);
      setMap(m);
      setErr(null);
    } catch (e) {
      setErr((e as Error).message || "Backend capability unavailable");
    }
  }, []);

  useEffect(() => {
    if (mode !== "live") {
      setErr("LIVE 时显示真实硬件探测。DEMO 不回放假设备。");
      return;
    }
    void load();
  }, [mode, load]);

  const runDiscovery = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/api/hardware/discovery`, { method: "POST" }).then((x) => x.json());
      setReport(r);
      await load();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="p-5">
      <div className="flex items-center justify-between">
        <h1 className="text-[18px] font-semibold">Hardware Lab</h1>
        <button
          className="rounded-sm border border-border px-3 py-1.5 text-[12px] hover:bg-accent disabled:opacity-50"
          disabled={busy || mode !== "live"}
          onClick={() => void runDiscovery()}
        >
          {busy ? "探测中…" : "运行硬件发现"}
        </button>
      </div>
      <p className="mt-1 text-[12px] text-muted-foreground">
        设备状态只来自真实探测：模糊 USB 信息只给平台提示，精确 MCU 需 SWD chip-id 证据。
      </p>
      {err && <div className="mt-3"><CapabilityBanner reason={err} /></div>}

      {devices && devices.length > 0 && (
        <section className="mt-5">
          <h2 className="text-[13px] font-medium">设备注册表</h2>
          <div className="mt-2 divide-y divide-border rounded-sm border border-border bg-panel">
            {devices.map((d) => (
              <div key={d.id} className="flex items-center justify-between px-3 py-2.5">
                <div>
                  <div className="font-mono text-[12px]">{d.id}</div>
                  <div className="text-[12px] text-muted-foreground">
                    {d.board || "UNKNOWN"} · {d.mcu || "UNKNOWN"}
                    {d.mcuEvidence ? ` (${d.mcuEvidence})` : ""} · probe={d.debugProbe || "—"} · port={d.serialPort || "—"}
                    {d.capabilities?.length ? ` · ${d.capabilities.join(", ")}` : ""}
                  </div>
                </div>
                <StatusBadge status={d.status} />
              </div>
            ))}
          </div>
        </section>
      )}

      {report?.probes && (
        <section className="mt-5">
          <h2 className="text-[13px] font-medium">
            发现报告{report.generatedAt ? ` · ${report.generatedAt}` : ""}
          </h2>
          <div className="mt-2 grid gap-2 md:grid-cols-2">
            <div className="rounded-sm border border-border bg-panel p-3">
              <div className="text-[12px] font-medium">调试探针</div>
              <ul className="mt-1 space-y-1 text-[12px] text-muted-foreground">
                {report.probes.map((p) => (
                  <li key={p.id}>
                    {p.label}: <span className="font-mono">{p.presence}</span>
                    {p.detail ? ` — ${p.detail}` : ""}
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-sm border border-border bg-panel p-3">
              <div className="text-[12px] font-medium">串口 (VID/PID)</div>
              {report.serialPorts && report.serialPorts.length > 0 ? (
                <ul className="mt-1 space-y-1 text-[12px] text-muted-foreground">
                  {report.serialPorts.map((p) => (
                    <li key={p.device}>
                      {p.device}: {p.usbName || p.description || "unknown"}
                      {p.vid ? ` [${p.vid}:${p.pid}]` : ""} · {p.kind || "unknown-kind"}
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="mt-1 text-[12px] text-muted-foreground">无串口</div>
              )}
            </div>
          </div>
          {report.nextSteps && report.nextSteps.length > 0 && (
            <div className="mt-2 rounded-sm border border-border bg-panel p-3">
              <div className="text-[12px] font-medium">下一步</div>
              <ul className="mt-1 list-disc pl-4 text-[12px] text-muted-foreground">
                {report.nextSteps.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {map?.available && map.devices && (
        <section className="mt-5">
          <h2 className="text-[13px] font-medium">hardware-map.yaml（计划清单）</h2>
          <div className="mt-2 rounded-sm border border-border bg-panel p-3 text-[12px] text-muted-foreground">
            {map.devices.map((d) => (
              <div key={d.id}>
                <span className="font-mono">{d.id}</span>: {d.board || "?"} · {d.serial || "—"} · {d.capabilities?.join(", ") || ""}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

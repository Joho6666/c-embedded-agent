import type { IocPin } from "@/types/ioc";

export function IocPinout({ pins, highlight }: { pins: IocPin[]; highlight?: string[] }) {
  if (!pins.length) {
    return <div className="text-[12px] text-muted-foreground">无引脚映射</div>;
  }
  return (
    <div className="overflow-hidden rounded-md border border-border">
      <table className="w-full text-left text-[12px]">
        <thead className="bg-panel-2 text-[11px] text-muted-foreground">
          <tr>
            <th className="px-2 py-1.5 font-medium">Pin</th>
            <th className="px-2 py-1.5 font-medium">Signal</th>
            <th className="px-2 py-1.5 font-medium">Mode</th>
          </tr>
        </thead>
        <tbody>
          {pins.map((p) => {
            const hot = highlight?.includes(p.pin);
            return (
              <tr key={`${p.pin}-${p.signal}`} className={hot ? "bg-warning/10" : "odd:bg-panel"}>
                <td className="px-2 py-1.5 font-mono">{p.pin}</td>
                <td className="px-2 py-1.5 font-mono">{p.signal}</td>
                <td className="px-2 py-1.5 text-muted-foreground">{p.mode ?? p.direction ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

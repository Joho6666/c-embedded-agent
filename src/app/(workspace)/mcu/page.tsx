"use client";

import Link from "next/link";
import { MCUInfo } from "@/components/mcu/MCUInfo";
import { MCUSelector } from "@/components/agent/MCUSelector";
import { currentMcu, mcuCatalog } from "@/lib/mock/hardware";
import { useHardware } from "@/lib/stores/hardware-store";
import { Button } from "@/components/ui/button";

export default function McuPage() {
  const name = useHardware((s) => s.context.mcu);
  const mcu = mcuCatalog.find((m) => m.name === name) ?? currentMcu;
  return (
    <div className="p-5">
      <div className="mb-4 flex justify-between">
        <h1 className="text-[18px] font-semibold">芯片信息</h1>
        <Button variant="outline" asChild>
          <Link href="/mcu/pins">Pin Configuration</Link>
        </Button>
      </div>
      <div className="mb-4">
        <MCUSelector />
      </div>
      <MCUInfo mcu={{ ...mcu, name }} />
    </div>
  );
}

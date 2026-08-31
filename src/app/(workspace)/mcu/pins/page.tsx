"use client";

import Link from "next/link";
import { PinMap } from "@/components/mcu/PinMap";
import { pinMap } from "@/lib/mock/mcu";
import { Button } from "@/components/ui/button";

export default function PinsPage() {
  return (
    <div className="p-5">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-semibold">Pin Configuration</h1>
          <p className="text-[12px] text-muted-foreground">STM32F103C8T6 · LQFP48 · PA5 = LED</p>
        </div>
        <Button variant="outline" asChild>
          <Link href="/mcu">返回芯片信息</Link>
        </Button>
      </div>
      <PinMap pins={pinMap} />
    </div>
  );
}

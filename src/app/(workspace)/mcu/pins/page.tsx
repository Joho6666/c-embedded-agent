"use client";

import Link from "next/link";
import { PinMap } from "@/components/mcu/PinMap";
import { MCUSelector } from "@/components/agent/MCUSelector";
import { pinMap } from "@/lib/mock/hardware";
import { Button } from "@/components/ui/button";

export default function PinsPage() {
  return (
    <div className="p-5">
      <div className="mb-4 flex justify-between">
        <h1 className="text-[18px] font-semibold">引脚配置</h1>
        <Button variant="outline" asChild>
          <Link href="/mcu">返回</Link>
        </Button>
      </div>
      <div className="mb-4">
        <MCUSelector />
      </div>
      <PinMap pins={pinMap} />
    </div>
  );
}

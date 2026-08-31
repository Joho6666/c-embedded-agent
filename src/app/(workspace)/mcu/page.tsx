"use client";

import Link from "next/link";
import { MCUInfo } from "@/components/mcu/MCUInfo";
import { currentMcu } from "@/lib/mock/mcu";
import { Button } from "@/components/ui/button";

export default function McuPage() {
  return (
    <div className="p-5">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-[18px] font-semibold">芯片</h1>
        <Button variant="outline" asChild>
          <Link href="/mcu/pins">Pin Configuration</Link>
        </Button>
      </div>
      <MCUInfo mcu={currentMcu} />
    </div>
  );
}

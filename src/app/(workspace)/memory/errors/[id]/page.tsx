"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ErrorMemoryDetailView } from "@/components/memory/ErrorMemoryDetail";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";
import { getErrorMemory } from "@/lib/api/memory";
import type { ErrorMemoryEntry } from "@/types/memory";
import { Button } from "@/components/ui/button";

export default function ErrorMemoryDetailPage() {
  const params = useParams<{ id: string }>();
  const [item, setItem] = useState<ErrorMemoryEntry | undefined>();
  const [reason, setReason] = useState<string | null>(null);

  useEffect(() => {
    void getErrorMemory(params.id).then((r) => {
      setItem(r.item);
      setReason(r.available ? null : r.reason ?? "Backend Not Implemented");
    });
  }, [params.id]);

  return (
    <div className="p-5">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-[18px] font-semibold">Error Memory Detail</h1>
        <Button variant="outline" asChild>
          <Link href="/memory/errors">返回</Link>
        </Button>
      </div>
      {reason && <CapabilityBanner reason={reason} />}
      {item && <ErrorMemoryDetailView item={item} />}
    </div>
  );
}

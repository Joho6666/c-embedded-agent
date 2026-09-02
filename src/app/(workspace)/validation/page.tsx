"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ValidationRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/debug");
  }, [router]);
  return <div className="p-4 text-[12px] text-muted-foreground">正在打开 Debug & Hardware Validation…</div>;
}

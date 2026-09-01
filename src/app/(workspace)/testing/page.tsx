"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function TestingRedirectPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/benchmark");
  }, [router]);
  return <div className="p-5 text-[12px] text-muted-foreground">Redirecting to Benchmark…</div>;
}

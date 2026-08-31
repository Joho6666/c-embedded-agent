"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      setError(j.detail || "登录失败");
      return;
    }
    router.push("/");
    router.refresh();
  }

  return (
    <div className="flex min-h-full items-center justify-center p-6">
      <form onSubmit={onSubmit} className="w-full max-w-sm space-y-3 rounded-lg border border-border bg-card p-5">
        <div>
          <h1 className="text-[18px] font-medium">Control Plane</h1>
          <p className="text-[12px] text-muted-foreground">Universal AI Gateway</p>
        </div>
        <div className="grid gap-1">
          <Label>Username</Label>
          <Input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
        </div>
        <div className="grid gap-1">
          <Label>Password</Label>
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
        </div>
        {error && <div className="text-[12px] text-error">{error}</div>}
        <Button className="w-full" type="submit">
          登录
        </Button>
      </form>
    </div>
  );
}

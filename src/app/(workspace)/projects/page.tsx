"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Empty } from "@/components/common/Empty";
import { StatusBadge } from "@/components/common/StatusBadge";
import { useLive } from "@/lib/stores/live-store";
import { createProject, loadProjects } from "@/lib/os/service";
import type { OsProject } from "@/types/os";
import { PROJECT_STATUS_LABEL } from "@/types/os";

export default function ProjectsPage() {
  const mode = useLive((s) => s.mode);
  const router = useRouter();
  const [items, setItems] = useState<OsProject[]>([]);
  const [name, setName] = useState("");

  useEffect(() => {
    void loadProjects().then(setItems);
  }, [mode]);

  return (
    <div className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-[18px] font-semibold">Projects</h1>
        <div className="flex gap-2">
          <Button variant="outline" asChild>
            <Link href="/start">Firmware Start Center</Link>
          </Button>
          <form
            className="flex gap-1"
            onSubmit={(e) => {
              e.preventDefault();
              const n = name.trim() || "Untitled project";
              void createProject({ name: n }).then((p) => {
                setName("");
                router.push(`/projects/${p.id}`);
              });
            }}
          >
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="New OS project"
              className="h-7 w-40 rounded-sm border border-border bg-background px-2 text-[12px]"
            />
            <Button type="submit">Create project</Button>
          </form>
        </div>
      </div>
      {items.length === 0 ? (
        <div className="mt-4">
          <Empty title="无项目" hint="Create project 或从 Start Center 建固件工程。" />
        </div>
      ) : (
        <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {items.map((p) => (
            <Link
              key={p.id}
              href={`/projects/${p.id}`}
              className="block rounded-md border border-border bg-panel p-3.5 hover:border-zinc-600 hover:bg-accent/30"
            >
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-[13px] font-medium">{p.name}</h3>
                <StatusBadge status={p.status} label={PROJECT_STATUS_LABEL[p.status]} />
              </div>
              <p className="mt-2 text-[12px] text-muted-foreground">{p.description || p.kind}</p>
              <div className="mt-3 flex justify-between text-[11px] text-muted-foreground">
                <span>{p.kind}</span>
                <span className="tabular-nums">{p.progress}%</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

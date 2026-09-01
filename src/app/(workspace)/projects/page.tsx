"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ProjectCard } from "@/components/project/ProjectCard";
import { Button } from "@/components/ui/button";
import { listProjects } from "@/lib/api/project";
import type { Project } from "@/types/project";
import { Empty } from "@/components/common/Empty";
import { useLive } from "@/lib/stores/live-store";

export default function ProjectsPage() {
  const mode = useLive((s) => s.mode);
  const [items, setItems] = useState<Project[]>([]);

  useEffect(() => {
    void listProjects().then(setItems);
  }, [mode]);

  return (
    <div className="p-5">
      <div className="flex items-center justify-between">
        <h1 className="text-[18px] font-semibold">项目列表</h1>
        <Button asChild>
          <Link href="/projects/new">新建项目</Link>
        </Button>
      </div>
      {items.length === 0 ? (
        <div className="mt-4">
          <Empty title="无项目" hint={mode === "live" ? "用「新建项目」或导入 CubeMX" : "DEMO 无本地工程列表"} />
        </div>
      ) : (
        <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {items.map((p) => (
            <ProjectCard key={p.id} project={p} />
          ))}
        </div>
      )}
    </div>
  );
}

"use client";

import Link from "next/link";
import { ProjectCard } from "@/components/project/ProjectCard";
import { Button } from "@/components/ui/button";
import { projects } from "@/lib/mock/projects";

export default function ProjectsPage() {
  return (
    <div className="p-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[18px] font-semibold">项目</h1>
          <p className="text-[12px] text-muted-foreground">{projects.length} 个工程</p>
        </div>
        <Button asChild>
          <Link href="/projects/new">新建项目</Link>
        </Button>
      </div>
      <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
        {projects.map((p) => (
          <ProjectCard key={p.id} project={p} />
        ))}
      </div>
    </div>
  );
}

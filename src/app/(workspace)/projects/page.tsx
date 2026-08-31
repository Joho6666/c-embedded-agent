"use client";

import Link from "next/link";
import { ProjectCard } from "@/components/project/ProjectCard";
import { Button } from "@/components/ui/button";
import { projects } from "@/lib/mock/projects";

export default function ProjectsPage() {
  return (
    <div className="p-5">
      <div className="flex items-center justify-between">
          <h1 className="text-[18px] font-semibold">项目列表</h1>
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

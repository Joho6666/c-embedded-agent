import Link from "next/link";
import type { Project } from "@/types/project";
import { StatusBadge } from "@/components/common/StatusBadge";

export function ProjectCard({ project }: { project: Project }) {
  const statusLabel =
    project.buildStatus === "passed"
      ? "✓ Build Passed"
      : project.buildStatus === "warning"
        ? `⚠ ${project.warningCount ?? 0} Warnings`
        : project.buildStatus === "failed"
          ? "✕ Build Failed"
          : project.buildStatus;

  return (
    <Link href="/agent" className="block rounded-sm border border-border bg-panel p-3 hover:border-zinc-600">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-[13px] font-medium">{project.name}</h3>
          <div className="font-mono text-[12px] text-muted-foreground">{project.mcu}</div>
        </div>
        <StatusBadge status={project.buildStatus} label={statusLabel} />
      </div>
      <p className="mt-2 text-[12px] text-muted-foreground">{project.description}</p>
      <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
        <div>Framework {project.framework}</div>
        <div>编译器 {project.compiler}</div>
        <div>创建 {project.createdAt}</div>
        <div>修改 {project.updatedAt}</div>
      </div>
    </Link>
  );
}

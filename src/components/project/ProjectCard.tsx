"use client";

import Link from "next/link";
import type { Project } from "@/types/project";
import { StatusBadge } from "@/components/common/StatusBadge";
import { useProject } from "@/lib/stores/project-store";
import { useHardware } from "@/lib/stores/hardware-store";
import { mcuCatalog } from "@/lib/mock/hardware";

export function ProjectCard({ project }: { project: Project }) {
  const setProjectId = useProject((s) => s.setProjectId);
  const setContext = useHardware((s) => s.setContext);
  const statusLabel =
    project.buildStatus === "passed"
      ? "✓ 构建通过"
      : project.buildStatus === "warning"
        ? `⚠ ${project.warningCount ?? 0} 个警告`
        : project.buildStatus === "failed"
          ? "✕ 构建失败"
          : project.buildStatus;

  return (
    <Link
      href="/workspace"
      onClick={() => {
        setProjectId(project.id);
        const m = mcuCatalog.find((x) => x.name === project.mcu);
        setContext({
          mcu: project.mcu,
          platform: project.platform,
          framework: project.framework,
          buildTool: project.compiler,
          rtos: project.rtos,
          core: m?.core,
          package: m?.package,
          flashKb: m?.flashKb,
          ramKb: m?.ramKb,
          clock: m?.frequency,
        });
      }}
      className="block rounded-md border border-border bg-panel p-3.5 transition-colors hover:border-zinc-600 hover:bg-accent/30"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-[13px] font-medium">{project.name}</h3>
          <div className="font-mono text-[12px] text-muted-foreground">{project.mcu}</div>
        </div>
        <StatusBadge status={project.buildStatus} label={statusLabel} />
      </div>
      <p className="mt-2 text-[12px] text-muted-foreground">{project.description}</p>
      <div className="mt-3 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
        <div>框架 {project.framework}</div>
        <div>编译器 {project.compiler}</div>
      </div>
    </Link>
  );
}

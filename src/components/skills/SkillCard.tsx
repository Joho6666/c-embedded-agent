import Link from "next/link";
import { StatusBadge } from "@/components/common/StatusBadge";
import type { EmbeddedSkill } from "@/types/skill";

export function SkillCard({ skill }: { skill: EmbeddedSkill }) {
  return (
    <Link href={`/skills/${skill.id}`} className="block rounded-md border border-border bg-panel p-3.5 hover:border-zinc-600">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-[13px] font-medium">{skill.name}</h3>
          <div className="font-mono text-[11px] text-muted-foreground">{skill.platform} · {skill.mcuFamilies.join(", ")}</div>
        </div>
        <StatusBadge status={skill.status === "ready" ? "ready" : "pending"} label={skill.status === "ready" ? "Ready" : "Draft"} />
      </div>
      <div className="mt-2 text-[11px] text-muted-foreground">Capabilities: {skill.capabilities.join(" · ") || "—"}</div>
      <dl className="mt-2 grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
        <div>Golden {skill.goldenExamples.length}</div>
        <div>Benchmark {skill.benchmarkScore == null ? "Not Tested" : `${skill.benchmarkScore}`}</div>
        <div>Known Issues {skill.knownErrors.length}</div>
        <div>v{skill.version}</div>
      </dl>
    </Link>
  );
}

import type { EmbeddedSkill } from "@/types/skill";

export function SkillDetailView({ skill }: { skill: EmbeddedSkill }) {
  return (
    <div className="space-y-5">
      <section>
        <h2 className="text-[13px] font-medium">Overview</h2>
        <p className="mt-1 text-[12px] text-muted-foreground">
          {skill.platform} / {skill.mcuFamilies.join(", ")} · {skill.peripherals.join(", ")}
        </p>
        <div className="mt-2 text-[12px]">Capabilities: {skill.capabilities.join(" · ")}</div>
      </section>
      <section>
        <h2 className="text-[13px] font-medium">Knowledge</h2>
        <ul className="mt-1 list-disc pl-4 text-[12px] text-muted-foreground">
          {skill.knowledgeCollections.map((k) => (
            <li key={k}>{k}</li>
          ))}
        </ul>
      </section>
      <section>
        <h2 className="text-[13px] font-medium">Golden Examples</h2>
        <div className="mt-1 space-y-1">
          {skill.goldenExamples.map((g) => (
            <div key={g.id} className="rounded-md border border-border bg-panel px-3 py-2">
              <div className="text-[13px]">{g.title}</div>
              <div className="text-[11px] text-muted-foreground">{g.summary}</div>
            </div>
          ))}
        </div>
      </section>
      <section>
        <h2 className="text-[13px] font-medium">Validation</h2>
        <ul className="mt-1 list-disc pl-4 text-[12px] text-muted-foreground">
          {skill.validators.map((v) => (
            <li key={v.id}>{v.label}</li>
          ))}
        </ul>
      </section>
      <section>
        <h2 className="text-[13px] font-medium">Known Errors</h2>
        {skill.knownErrors.length === 0 ? (
          <div className="text-[12px] text-muted-foreground">无记录</div>
        ) : (
          <ul className="mt-1 space-y-1 text-[12px]">
            {skill.knownErrors.map((e) => (
              <li key={e.pattern} className="rounded-md border border-border bg-panel px-3 py-2">
                <div className="font-mono">{e.pattern}</div>
                <div className="text-[11px] text-muted-foreground">{e.hint}</div>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section>
        <h2 className="text-[13px] font-medium">Benchmarks</h2>
        <div className="text-[12px] text-muted-foreground">{skill.benchmarkScore == null ? "Not Tested" : String(skill.benchmarkScore)}</div>
      </section>
    </div>
  );
}

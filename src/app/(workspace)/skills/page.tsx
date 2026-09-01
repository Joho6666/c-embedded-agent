"use client";

import { useEffect, useState } from "react";
import { SkillCard } from "@/components/skills/SkillCard";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";
import { Empty } from "@/components/common/Empty";
import { listSkills } from "@/lib/api/skills";
import type { EmbeddedSkill } from "@/types/skill";
import { useLive } from "@/lib/stores/live-store";

export default function SkillsPage() {
  const mode = useLive((s) => s.mode);
  const [skills, setSkills] = useState<EmbeddedSkill[]>([]);
  const [reason, setReason] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== "live") {
      setReason("Backend capability unavailable");
      setSkills([]);
      return;
    }
    void listSkills().then((r) => {
      setSkills(r.skills);
      setReason(r.available ? null : r.reason ?? "Backend Not Implemented");
    });
  }, [mode]);

  return (
    <div className="p-5">
      <h1 className="text-[18px] font-semibold">Embedded Skills</h1>
      <p className="text-[12px] text-muted-foreground">专业外设能力包，不是插件商城。</p>
      {reason && <div className="mt-3"><CapabilityBanner reason={reason} /></div>}
      {skills.length === 0 && !reason ? <div className="mt-4"><Empty title="无 Skills" /></div> : null}
      <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
        {skills.map((s) => (
          <SkillCard key={s.id} skill={s} />
        ))}
      </div>
    </div>
  );
}

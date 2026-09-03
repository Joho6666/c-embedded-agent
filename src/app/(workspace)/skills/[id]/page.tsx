"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { SkillDetailView } from "@/components/skills/SkillDetail";
import { CapabilityBanner } from "@/components/common/CapabilityBanner";
import { getSkill } from "@/lib/api/skills";
import type { EmbeddedSkill } from "@/types/skill";
import { Button } from "@/components/ui/button";

export default function SkillDetailPage() {
  const params = useParams<{ id: string }>();
  const [skill, setSkill] = useState<EmbeddedSkill | undefined>();
  const [reason, setReason] = useState<string | null>(null);

  useEffect(() => {
    void getSkill(params.id).then((r) => {
      setSkill(r.skill);
      setReason(r.available ? null : r.reason ?? "Backend Not Implemented");
    });
  }, [params.id]);

  return (
    <div className="p-5">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-[18px] font-semibold">{skill?.name ?? "Skill"}</h1>
        <Button variant="outline" asChild>
          <Link href="/skills">返回</Link>
        </Button>
      </div>
      {reason && <CapabilityBanner reason={reason} />}
      {skill && <SkillDetailView skill={skill} />}
    </div>
  );
}

export interface SkillGoldenExample {
  id: string;
  title: string;
  summary: string;
}

export interface SkillValidator {
  id: string;
  label: string;
}

export interface SkillKnownError {
  pattern: string;
  hint: string;
}

export interface EmbeddedSkill {
  id: string;
  name: string;
  platform: string;
  mcuFamilies: string[];
  peripherals: string[];
  capabilities: string[];
  knowledgeCollections: string[];
  goldenExamples: SkillGoldenExample[];
  validators: SkillValidator[];
  knownErrors: SkillKnownError[];
  benchmarkScore: number | null;
  version: string;
  enabled: boolean;
  status: "ready" | "draft";
}

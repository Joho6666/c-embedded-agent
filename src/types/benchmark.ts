export interface SkillScore {
  skillId: string;
  name: string;
  compileSuccess: number | null;
  tested: boolean;
}

export interface ModelComparisonRow {
  model: string;
  compileSuccess: number | null;
  tokens: number | null;
  cost: number | null;
  iterations: number | null;
}

export interface BenchmarkSummary {
  available: boolean;
  reason?: string;
  mcu?: string;
  tasks?: number | null;
  compileSuccess?: number | null;
  firstBuildSuccess?: number | null;
  autoFix?: number | null;
  avgIterations?: number | null;
  skipped?: string[];
  bySkill: SkillScore[];
  models: ModelComparisonRow[];
  gcc?: boolean;
  llm?: boolean;
}

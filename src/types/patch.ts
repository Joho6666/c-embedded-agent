export type PatchStatus = "pending" | "accepted" | "rejected";

export interface PatchWhy {
  sources: string[];
  summary: string;
}

export interface CodePatch {
  id: string;
  runId: string;
  path: string;
  original: string;
  proposed: string;
  status: PatchStatus;
  reason: string;
  createdAt: string;
  approvalId?: string;
  why?: PatchWhy;
}

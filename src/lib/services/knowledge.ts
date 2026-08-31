import { sleep } from "@/lib/utils";
import { knowledgeDocs } from "@/lib/mock/knowledge";
import type { KnowledgeDoc } from "@/types/knowledge";

export async function listKnowledge(): Promise<KnowledgeDoc[]> {
  await sleep(60);
  return knowledgeDocs;
}

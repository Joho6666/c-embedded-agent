import { sleep } from "@/lib/utils";
import { knowledgeDocs } from "@/lib/mock/knowledge";

export async function listKnowledge() {
  await sleep(30);
  return knowledgeDocs;
}

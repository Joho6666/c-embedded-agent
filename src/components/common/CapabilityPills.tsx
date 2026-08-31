import { Badge } from "@/components/ui/badge";

const labels: Record<string, string> = {
  chat: "Chat",
  responses: "Responses",
  tools: "Tools",
  vision: "Vision",
  image: "Image",
  embedding: "Embedding",
  audio: "Audio",
  agent: "Agent",
  coding: "Coding",
  reasoning: "Reasoning",
  streaming: "Streaming",
  json: "JSON",
};

export function CapabilityPills({ items, max = 8 }: { items: string[]; max?: number }) {
  return (
    <div className="flex flex-wrap gap-1">
      {items.slice(0, max).map((c) => (
        <Badge key={c} className="capitalize">
          {labels[c] ?? c}
        </Badge>
      ))}
      {items.length > max && <Badge>+{items.length - max}</Badge>}
    </div>
  );
}

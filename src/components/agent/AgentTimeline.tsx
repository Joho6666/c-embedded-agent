import type { AgentEvent } from "@/types/events";
import { AgentEventCard } from "./AgentEventCard";

export function AgentTimeline({ events }: { events: AgentEvent[] }) {
  if (events.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border bg-panel/50 p-10 text-center text-[13px] text-muted-foreground">
        尚未开始。点击「运行 Agent」或「STM32 LED 演示」，将按真实 Run 事件流执行。
      </div>
    );
  }
  return (
    <div className="space-y-2">
      {events
        .filter((e) => e.description !== "__run_end__")
        .map((e) => (
          <AgentEventCard key={e.id} event={e} />
        ))}
    </div>
  );
}

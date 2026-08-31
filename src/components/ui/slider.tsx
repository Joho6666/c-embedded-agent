"use client";

import * as SliderPrimitive from "@radix-ui/react-slider";
import { cn } from "@/lib/utils";

export function Slider({ className, ...props }: React.ComponentProps<typeof SliderPrimitive.Root>) {
  return (
    <SliderPrimitive.Root className={cn("relative flex h-5 w-full touch-none items-center", className)} {...props}>
      <SliderPrimitive.Track className="relative h-1 w-full grow rounded-sm bg-muted">
        <SliderPrimitive.Range className="absolute h-full rounded-sm bg-primary" />
      </SliderPrimitive.Track>
      <SliderPrimitive.Thumb className="block size-3.5 rounded-full border border-border bg-white shadow" />
    </SliderPrimitive.Root>
  );
}

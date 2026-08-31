"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export const Sheet = DialogPrimitive.Root;
export const SheetTrigger = DialogPrimitive.Trigger;
export const SheetClose = DialogPrimitive.Close;

export function SheetContent({
  className,
  children,
  title,
  description,
}: {
  className?: string;
  children: React.ReactNode;
  title?: string;
  description?: string;
}) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/50" />
      <DialogPrimitive.Content
        className={cn(
          "fixed top-0 right-0 z-50 flex h-full w-[min(520px,100vw)] flex-col border-l border-border bg-card shadow-2xl",
          className,
        )}
      >
        <div className="flex items-start justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            {title && <DialogPrimitive.Title className="text-[13px] font-medium">{title}</DialogPrimitive.Title>}
            {description && (
              <DialogPrimitive.Description className="mt-0.5 text-[11px] text-muted-foreground">
                {description}
              </DialogPrimitive.Description>
            )}
          </div>
          <DialogPrimitive.Close className="rounded-sm p-1 text-muted-foreground hover:bg-accent">
            <X className="size-3.5" />
          </DialogPrimitive.Close>
        </div>
        <div className="flex-1 overflow-auto p-4">{children}</div>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

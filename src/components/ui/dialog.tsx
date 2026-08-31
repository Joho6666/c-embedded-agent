"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

export function DialogContent({
  className,
  children,
  title,
  description,
  wide,
}: {
  className?: string;
  children: React.ReactNode;
  title?: string;
  description?: string;
  wide?: boolean;
}) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/55 backdrop-blur-[2px]" />
      <DialogPrimitive.Content
        className={cn(
          "fixed top-1/2 left-1/2 z-50 max-h-[88vh] w-[min(560px,calc(100vw-24px))] -translate-x-1/2 -translate-y-1/2 overflow-auto rounded-lg border border-border bg-card shadow-2xl",
          wide && "w-[min(880px,calc(100vw-24px))]",
          className,
        )}
      >
        {(title || description) && (
          <div className="flex items-start justify-between gap-3 border-b border-border px-4 py-3">
            <div>
              {title && (
                <DialogPrimitive.Title className="text-[13px] font-medium">{title}</DialogPrimitive.Title>
              )}
              {description && (
                <DialogPrimitive.Description className="mt-0.5 text-[11px] text-muted-foreground">
                  {description}
                </DialogPrimitive.Description>
              )}
            </div>
            <DialogPrimitive.Close className="rounded-sm p-1 text-muted-foreground hover:bg-accent hover:text-foreground">
              <X className="size-3.5" />
            </DialogPrimitive.Close>
          </div>
        )}
        <div className="p-4">{children}</div>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

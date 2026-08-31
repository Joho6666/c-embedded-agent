"use client";

import { useEffect } from "react";
import { useWorkspace } from "@/lib/stores/workspace";

export function KeyboardShortcuts() {
  const runBuild = useWorkspace((s) => s.runBuild);
  const runFlash = useWorkspace((s) => s.runFlash);
  const toggleBottom = useWorkspace((s) => s.toggleBottom);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const meta = e.ctrlKey || e.metaKey;
      if (meta && e.key.toLowerCase() === "b") {
        e.preventDefault();
        runBuild();
      }
      if (meta && e.shiftKey && e.key.toLowerCase() === "f") {
        e.preventDefault();
        runFlash();
      }
      if (meta && e.key === "`") {
        e.preventDefault();
        toggleBottom();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [runBuild, runFlash, toggleBottom]);

  return null;
}

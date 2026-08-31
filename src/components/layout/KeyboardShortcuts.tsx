"use client";

import { useEffect } from "react";
import { useWorkspaceUI } from "@/lib/stores/workspace-store";
import { useEditor } from "@/lib/stores/editor-store";
import { useTerminal } from "@/lib/stores/terminal-store";

export function KeyboardShortcuts() {
  const toggleBottom = useWorkspaceUI((s) => s.toggleBottom);
  const setBottomTab = useWorkspaceUI((s) => s.setBottomTab);
  const saveFile = useEditor((s) => s.saveFile);
  const appendTerminal = useTerminal((s) => s.appendTerminal);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const meta = e.ctrlKey || e.metaKey;
      if (meta && e.key.toLowerCase() === "s") {
        e.preventDefault();
        saveFile();
      }
      if (meta && e.key.toLowerCase() === "b") {
        e.preventDefault();
        setBottomTab("build");
        appendTerminal(["$ make -j8"]);
      }
      if (meta && e.shiftKey && e.key.toLowerCase() === "f") {
        e.preventDefault();
        setBottomTab("terminal");
        appendTerminal(["$ STM32_Programmer_CLI -c port=SWD"]);
      }
      if (meta && e.key === "`") {
        e.preventDefault();
        toggleBottom();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [appendTerminal, saveFile, setBottomTab, toggleBottom]);

  return null;
}

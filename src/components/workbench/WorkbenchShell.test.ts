import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";

describe("Workbench shell", () => {
  it("workspace page contains activity regions", () => {
    const src = readFileSync(path.join(process.cwd(), "src/app/(workspace)/workspace/page.tsx"), "utf8");
    expect(src).toContain("Explorer");
    expect(src).toContain("CodeEditor");
    expect(src).toContain("ContextPanel");
  });

  it("toolbar uses real flash API not STM32_Programmer_CLI", () => {
    const src = readFileSync(path.join(process.cwd(), "src/components/workbench/ToolBar.tsx"), "utf8");
    expect(src).toContain("flashProject");
    expect(src).not.toContain("STM32_Programmer_CLI");
  });
});

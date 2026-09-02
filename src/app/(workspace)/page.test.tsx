import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";

describe("Start Center source", () => {
  const src = readFileSync(path.join(process.cwd(), "src/app/(workspace)/page.tsx"), "utf8");

  it("is a start center not a KPI dashboard", () => {
    expect(src).toContain("欢迎使用 C-Agent Workbench 2.0");
    expect(src).toContain("AI Project Intake");
    expect(src).toContain("Recent Projects");
    expect(src).toContain("Environment");
    expect(src).not.toContain("Engineering Dashboard");
  });

  it("does not fake all-green environment", () => {
    expect(src).toContain("不会显示全部正常");
    expect(src).toContain("UNKNOWN");
  });
});

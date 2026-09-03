import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";

describe("Today page", () => {
  const src = readFileSync(path.join(process.cwd(), "src/app/(workspace)/page.tsx"), "utf8");

  it("is a today command surface not a KPI dashboard", () => {
    expect(src).toContain("MyOS · Today");
    expect(src).toContain("Agent Running");
    expect(src).toContain("Needs Review");
    expect(src).toContain("Today’s Focus");
    expect(src).not.toContain("Engineering Dashboard");
  });

  it("links to firmware start center", () => {
    expect(src).toContain('href="/start"');
    expect(src).toContain("Create project");
  });
});

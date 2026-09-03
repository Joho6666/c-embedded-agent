import { describe, expect, it } from "vitest";
import { navItems } from "./nav";

describe("primary nav", () => {
  it("starts with Today and keeps workspace", () => {
    expect(navItems.map((n) => n.href)).toEqual(["/", "/projects", "/workspace", "/agent", "/knowledge", "/settings"]);
    expect(navItems[0].label).toBe("Today");
  });
});

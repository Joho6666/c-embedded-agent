import { describe, expect, it } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { StatusBadge } from "./StatusBadge";
import { ValidationTimeline } from "@/components/hardware/ValidationTimeline";
import { CapabilityBadge } from "@/components/platform/CapabilityBadge";

describe("status rendering", () => {
  it("renders PASS/FAIL/PARTIAL/UNKNOWN without inventing success", () => {
    const html = ["pass", "fail", "partial", "unknown", "unavailable", "not_tested"]
      .map((s) => renderToStaticMarkup(<StatusBadge status={s} />))
      .join(" ");
    expect(html).toContain("PASS");
    expect(html).toContain("FAIL");
    expect(html).toContain("PARTIAL");
    expect(html).toContain("UNKNOWN");
    expect(html).toContain("UNAVAILABLE");
    expect(html).toContain("NOT TESTED");
  });

  it("validation timeline is not_tested without a run", () => {
    const html = renderToStaticMarkup(<ValidationTimeline />);
    expect(html).toContain("NOT TESTED");
    expect(html).not.toMatch(/>PASS</);
  });

  it("capability badge distinguishes planned platforms", () => {
    const html = renderToStaticMarkup(<CapabilityBadge status="planned" />);
    expect(html).toContain("Planned");
  });
});

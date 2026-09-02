import { describe, expect, it } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { PlatformSelector } from "./PlatformSelector";
import { getPlatform } from "@/lib/platform";

describe("PlatformSelector", () => {
  it("renders all platforms with honest status labels", () => {
    const html = renderToStaticMarkup(<PlatformSelector value="stm32" onChange={() => undefined} />);
    expect(html).toContain("STM32");
    expect(html).toContain("ESP32");
    expect(html).toContain("C51");
    expect(html).toContain("Host C");
    expect(html).toContain("Beta");
    expect(html).toContain("Planned");
  });

  it("C51 skills exclude wireless", () => {
    expect(getPlatform("c51").skills.includes("Wi-Fi")).toBe(false);
  });
});

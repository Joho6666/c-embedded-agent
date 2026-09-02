import { describe, expect, it } from "vitest";
import { getPlatform, normalizePlatformId, PLATFORMS } from "./catalog";

describe("platform catalog", () => {
  it("marks only STM32 as supported", () => {
    const supported = PLATFORMS.filter((p) => p.supported).map((p) => p.id);
    expect(supported).toEqual(["stm32"]);
  });

  it("does not offer Wi-Fi on C51", () => {
    expect(getPlatform("c51").skills).not.toContain("Wi-Fi");
    expect(getPlatform("c51").skills).not.toContain("BLE");
  });

  it("does not offer ST-Link on Host C", () => {
    const host = getPlatform("host-c");
    expect(host.flashAdapters).toEqual([]);
    expect(host.skills).toEqual([]);
    expect(host.debugAdapters.some((d) => /st-?link/i.test(d.label))).toBe(false);
  });

  it("normalizes legacy platform ids", () => {
    expect(normalizePlatformId("STM32")).toBe("stm32");
    expect(normalizePlatformId("8051")).toBe("c51");
    expect(normalizePlatformId("Linux")).toBe("host-c");
  });
});
